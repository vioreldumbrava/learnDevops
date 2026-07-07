// Package controller holds the "behavior half" of the operator: the reconcile
// loop that makes the world match every DojoBackup's spec.
//
// The one idea that matters: reconciliation is LEVEL-based, not EDGE-based.
// We are not handed "the user changed X" events to react to — we are handed a
// NAME, we read the current desired state (the CR) and the current actual
// state (the CronJob/PVC), and we converge actual toward desired. Written that
// way, the same code handles create, update, external tampering, controller
// restarts, and missed events. That is why deleting the operator's CronJob by
// hand just makes it come back (lab 02's "aha" moment).
package controller

import (
	"context"
	"fmt"
	"time"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/tools/record"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	dojov1alpha1 "github.com/devops-dojo/dojo-operator/api/v1alpha1"
)

const (
	// Finalizer: our "pre-delete hook". While this string sits in
	// metadata.finalizers, the API server will NOT remove the object — it sets
	// deletionTimestamp and waits for us to finish our cleanup and remove the
	// entry. We use it to refuse deletion while a backup Job is still running
	// (lab 04). A bug that forgets to remove a finalizer is THE classic cause
	// of namespaces stuck in Terminating.
	finalizerName = "dojo.dev/backup-protection"

	// requeueStatus: how often we re-check child Jobs to refresh status even
	// when nothing we watch has changed. A production operator would watch the
	// Jobs themselves; polling keeps this teaching controller small.
	requeueStatus = 30 * time.Second
)

// DojoBackupReconciler reconciles DojoBackup objects.
type DojoBackupReconciler struct {
	client.Client                   // reads hit a local CACHE, writes go to the API server
	Scheme        *runtime.Scheme   // Go type <-> group/version/kind registry
	Recorder      record.EventRecorder // emits the Events shown by `kubectl describe`
}

// The kubebuilder RBAC markers below are the source of truth for
// config/rbac/role.yaml — everything the operator may touch, and nothing more.
// Note there is NO rule for secrets: the backup pod mounts the secret, the
// operator never reads it.
//
// +kubebuilder:rbac:groups=dojo.dev,resources=dojobackups,verbs=get;list;watch;update;patch
// +kubebuilder:rbac:groups=dojo.dev,resources=dojobackups/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=dojo.dev,resources=dojobackups/finalizers,verbs=update
// +kubebuilder:rbac:groups=batch,resources=cronjobs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=batch,resources=jobs,verbs=get;list;watch
// +kubebuilder:rbac:groups="",resources=persistentvolumeclaims,verbs=get;list;watch;create
// +kubebuilder:rbac:groups="",resources=events,verbs=create;patch

// Reconcile is called with a name whenever anything relevant changes (the CR
// itself, or a CronJob we own), and must be IDEMPOTENT: running it twice in a
// row must be a no-op the second time.
func (r *DojoBackupReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	// 1. Fetch the CR. NotFound is normal (it was deleted and the finalizer
	//    already ran) — never an error.
	backup := &dojov1alpha1.DojoBackup{}
	if err := r.Get(ctx, req.NamespacedName, backup); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// 2. Deletion path: deletionTimestamp is set the moment someone runs
	//    `kubectl delete`, but the object lingers until finalizers are gone.
	if !backup.DeletionTimestamp.IsZero() {
		return r.handleDeletion(ctx, backup)
	}

	// 3. Make sure our finalizer is present BEFORE creating children, so we
	//    can never be deleted without getting a chance to check running Jobs.
	if controllerutil.AddFinalizer(backup, finalizerName) {
		if err := r.Update(ctx, backup); err != nil {
			return ctrl.Result{}, err
		}
		// The update bumps resourceVersion and triggers a fresh Reconcile;
		// stop here and let that one do the real work on current data.
		return ctrl.Result{}, nil
	}

	// 4. Ensure the PVC that stores the dumps exists. Create-if-missing only:
	//    PVC sizes can't shrink and resizing is storage-class dependent, so we
	//    deliberately don't try to update it.
	if err := r.ensurePVC(ctx, backup); err != nil {
		return r.failStatus(ctx, backup, "PVCFailed", err)
	}

	// 5. Ensure the CronJob matches the spec. CreateOrUpdate computes desired
	//    state and diffs it against the cluster — the convergence step.
	cronJob := &batchv1.CronJob{ObjectMeta: metav1.ObjectMeta{
		Name:      backup.Name + "-backup",
		Namespace: backup.Namespace,
	}}
	op, err := controllerutil.CreateOrUpdate(ctx, r.Client, cronJob, func() error {
		r.buildCronJob(backup, cronJob)
		// The ownerReference is what makes garbage collection work: delete the
		// DojoBackup and Kubernetes deletes the CronJob (and its Jobs) for us.
		// It is also what routes CronJob events back to THIS reconciler.
		return controllerutil.SetControllerReference(backup, cronJob, r.Scheme)
	})
	if err != nil {
		return r.failStatus(ctx, backup, "CronJobFailed", err)
	}
	if op != controllerutil.OperationResultNone {
		logger.Info("cronjob reconciled", "operation", op)
		r.Recorder.Eventf(backup, corev1.EventTypeNormal, "Reconciled", "CronJob %s %s", cronJob.Name, op)
	}

	// 6. Observe children and publish status. Status is OUR report to the
	//    user; it must be written through the /status subresource.
	if err := r.updateStatus(ctx, backup, cronJob); err != nil {
		return ctrl.Result{}, err
	}

	// 7. Come back periodically to refresh status from the Jobs.
	return ctrl.Result{RequeueAfter: requeueStatus}, nil
}

// handleDeletion refuses to let the CR go while a backup Job is mid-flight,
// then removes the finalizer so deletion (and ownerRef GC) can proceed.
func (r *DojoBackupReconciler) handleDeletion(ctx context.Context, backup *dojov1alpha1.DojoBackup) (ctrl.Result, error) {
	logger := log.FromContext(ctx)
	if !controllerutil.ContainsFinalizer(backup, finalizerName) {
		return ctrl.Result{}, nil // nothing left to do; API server finishes the delete
	}
	active, err := r.countActiveJobs(ctx, backup)
	if err != nil {
		return ctrl.Result{}, err
	}
	if active > 0 {
		logger.Info("deletion blocked: backup job still running", "activeJobs", active)
		r.Recorder.Event(backup, corev1.EventTypeWarning, "DeletionBlocked",
			"waiting for running backup job(s) to finish")
		return ctrl.Result{RequeueAfter: requeueStatus}, nil
	}
	controllerutil.RemoveFinalizer(backup, finalizerName)
	return ctrl.Result{}, r.Update(ctx, backup)
}

// ensurePVC creates the backup volume once. ownerRef included: deleting the
// DojoBackup deletes the dumps too — that's a deliberate, documented choice
// (a real product might orphan the PVC instead; lab 04 discusses the trade-off).
func (r *DojoBackupReconciler) ensurePVC(ctx context.Context, backup *dojov1alpha1.DojoBackup) error {
	pvc := &corev1.PersistentVolumeClaim{}
	name := types.NamespacedName{Name: backup.Name + "-backups", Namespace: backup.Namespace}
	err := r.Get(ctx, name, pvc)
	if err == nil {
		return nil // exists — leave it alone
	}
	if !apierrors.IsNotFound(err) {
		return err
	}
	size, err := resource.ParseQuantity(storageSize(backup))
	if err != nil {
		return fmt.Errorf("bad storageSize %q: %w", backup.Spec.StorageSize, err)
	}
	pvc = &corev1.PersistentVolumeClaim{
		ObjectMeta: metav1.ObjectMeta{Name: name.Name, Namespace: name.Namespace},
		Spec: corev1.PersistentVolumeClaimSpec{
			AccessModes: []corev1.PersistentVolumeAccessMode{corev1.ReadWriteOnce},
			Resources: corev1.VolumeResourceRequirements{
				Requests: corev1.ResourceList{corev1.ResourceStorage: size},
			},
		},
	}
	if err := controllerutil.SetControllerReference(backup, pvc, r.Scheme); err != nil {
		return err
	}
	r.Recorder.Eventf(backup, corev1.EventTypeNormal, "PVCCreated", "created %s (%s)", name.Name, size.String())
	return r.Create(ctx, pvc)
}

// buildCronJob fills in the desired CronJob. Everything here is derived from
// spec — change the spec, and CreateOrUpdate patches the CronJob to match.
// The pod is plain lab-07 material: pg_dump to a timestamped file, then prune
// to the newest N. Password comes from a secretKeyRef — the operator wires the
// REFERENCE; only the pod ever sees the value.
func (r *DojoBackupReconciler) buildCronJob(backup *dojov1alpha1.DojoBackup, cj *batchv1.CronJob) {
	db := backup.Spec.Database
	port := db.Port
	if port == 0 {
		port = 5432
	}
	script := fmt.Sprintf(
		`set -eu
FILE=/backups/%s_$(date +%%Y%%m%%d_%%H%%M%%S).sql
pg_dump -h %s -p %d -U %s -d %s -F p -f "$FILE"
echo "backup written: $FILE"
ls -1t /backups/%s_*.sql | tail -n +%d | xargs -r rm -v`,
		db.Name, db.Host, port, db.User, db.Name, db.Name, retention(backup)+1)

	cj.Spec.Schedule = backup.Spec.Schedule
	cj.Spec.Suspend = backup.Spec.Suspend
	cj.Spec.ConcurrencyPolicy = batchv1.ForbidConcurrent // two pg_dumps at once help nobody
	// Keep a little history so `kubectl get jobs` shows recent runs in lab 03.
	three, one := int32(3), int32(1)
	cj.Spec.SuccessfulJobsHistoryLimit = &three
	cj.Spec.FailedJobsHistoryLimit = &one

	cj.Spec.JobTemplate.Spec.Template.Spec = corev1.PodSpec{
		RestartPolicy: corev1.RestartPolicyNever,
		Containers: []corev1.Container{{
			Name:    "pg-dump",
			Image:   "postgres:16-alpine",
			Command: []string{"sh", "-c", script},
			Env: []corev1.EnvVar{{
				Name: "PGPASSWORD",
				ValueFrom: &corev1.EnvVarSource{
					SecretKeyRef: &corev1.SecretKeySelector{
						LocalObjectReference: corev1.LocalObjectReference{Name: db.PasswordSecret.Name},
						Key:                  db.PasswordSecret.Key,
					},
				},
			}},
			VolumeMounts: []corev1.VolumeMount{{Name: "backups", MountPath: "/backups"}},
			Resources: corev1.ResourceRequirements{ // Kyverno (lab 29) requires limits
				Requests: corev1.ResourceList{
					corev1.ResourceCPU:    resource.MustParse("25m"),
					corev1.ResourceMemory: resource.MustParse("64Mi"),
				},
				Limits: corev1.ResourceList{
					corev1.ResourceCPU:    resource.MustParse("500m"),
					corev1.ResourceMemory: resource.MustParse("256Mi"),
				},
			},
		}},
		Volumes: []corev1.Volume{{
			Name: "backups",
			VolumeSource: corev1.VolumeSource{
				PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
					ClaimName: backup.Name + "-backups",
				},
			},
		}},
	}
	// The app label satisfies the Kyverno require-app-label policy (lab 29)
	// and gives NetworkPolicies (lab 28) something to select.
	if cj.Spec.JobTemplate.Spec.Template.Labels == nil {
		cj.Spec.JobTemplate.Spec.Template.Labels = map[string]string{}
	}
	cj.Spec.JobTemplate.Spec.Template.Labels["app"] = "dojo-backup"
}

// updateStatus reads the child Jobs and publishes what we observed.
func (r *DojoBackupReconciler) updateStatus(ctx context.Context, backup *dojov1alpha1.DojoBackup, cj *batchv1.CronJob) error {
	jobs := &batchv1.JobList{}
	if err := r.List(ctx, jobs, client.InNamespace(backup.Namespace)); err != nil {
		return err
	}
	var active int32
	var lastSuccess *metav1.Time
	for i := range jobs.Items {
		job := &jobs.Items[i]
		if !ownedByCronJob(job, cj.Name) {
			continue
		}
		active += job.Status.Active
		if job.Status.CompletionTime != nil {
			if lastSuccess == nil || job.Status.CompletionTime.After(lastSuccess.Time) {
				lastSuccess = job.Status.CompletionTime
			}
		}
	}

	backup.Status.ActiveJobs = active
	backup.Status.LastScheduleTime = cj.Status.LastScheduleTime
	if lastSuccess != nil {
		backup.Status.LastSuccessfulTime = lastSuccess
	}
	backup.Status.ObservedGeneration = backup.Generation
	meta.SetStatusCondition(&backup.Status.Conditions, metav1.Condition{
		Type:               "Ready",
		Status:             metav1.ConditionTrue,
		Reason:             "CronJobReconciled",
		Message:            fmt.Sprintf("CronJob %s matches spec", cj.Name),
		ObservedGeneration: backup.Generation,
	})
	// Status().Update goes through the /status subresource — a plain Update
	// would be rejected for status changes once the subresource is enabled.
	return r.Status().Update(ctx, backup)
}

// failStatus records a failure as a condition + event, then returns the error
// so controller-runtime retries with exponential backoff.
func (r *DojoBackupReconciler) failStatus(ctx context.Context, backup *dojov1alpha1.DojoBackup, reason string, err error) (ctrl.Result, error) {
	r.Recorder.Event(backup, corev1.EventTypeWarning, reason, err.Error())
	meta.SetStatusCondition(&backup.Status.Conditions, metav1.Condition{
		Type:               "Ready",
		Status:             metav1.ConditionFalse,
		Reason:             reason,
		Message:            err.Error(),
		ObservedGeneration: backup.Generation,
	})
	if statusErr := r.Status().Update(ctx, backup); statusErr != nil {
		log.FromContext(ctx).Error(statusErr, "failed to record failure condition")
	}
	return ctrl.Result{}, err
}

func (r *DojoBackupReconciler) countActiveJobs(ctx context.Context, backup *dojov1alpha1.DojoBackup) (int32, error) {
	jobs := &batchv1.JobList{}
	if err := r.List(ctx, jobs, client.InNamespace(backup.Namespace)); err != nil {
		return 0, err
	}
	var active int32
	for i := range jobs.Items {
		if ownedByCronJob(&jobs.Items[i], backup.Name+"-backup") {
			active += jobs.Items[i].Status.Active
		}
	}
	return active, nil
}

// ownedByCronJob walks a Job's ownerReferences looking for our CronJob —
// the same parent/child chain `kubectl get -o yaml` shows under metadata.
func ownedByCronJob(job *batchv1.Job, cronJobName string) bool {
	for _, ref := range job.OwnerReferences {
		if ref.Kind == "CronJob" && ref.Name == cronJobName {
			return true
		}
	}
	return false
}

func retention(b *dojov1alpha1.DojoBackup) int32 {
	if b.Spec.Retention <= 0 {
		return 5
	}
	return b.Spec.Retention
}

func storageSize(b *dojov1alpha1.DojoBackup) string {
	if b.Spec.StorageSize == "" {
		return "1Gi"
	}
	return b.Spec.StorageSize
}

// SetupWithManager wires the controller into the manager:
//   For(DojoBackup)  — reconcile when a DojoBackup changes;
//   Owns(CronJob)    — ALSO reconcile the owning DojoBackup when a CronJob we
//                      created changes (that's how hand-deleting the CronJob
//                      triggers its own resurrection).
func (r *DojoBackupReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&dojov1alpha1.DojoBackup{}).
		Owns(&batchv1.CronJob{}).
		Named("dojobackup").
		Complete(r)
}
