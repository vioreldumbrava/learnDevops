// Unit tests with controller-runtime's FAKE client: an in-memory API server
// stand-in. No cluster, no binaries — `go test` and milliseconds. The
// trade-off: the fake client doesn't run admission/defaulting/GC, so these
// tests prove OUR logic (what Reconcile creates and writes), while lab 02–05
// prove the integration against a real kind cluster. Both layers matter;
// neither replaces the other.
package controller

import (
	"context"
	"testing"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/tools/record"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"

	dojov1alpha1 "github.com/devops-dojo/dojo-operator/api/v1alpha1"
)

// newTestReconciler builds a reconciler around a fake client pre-loaded with
// the given objects — the standard fixture pattern for controller tests.
func newTestReconciler(t *testing.T, objs ...client.Object) (*DojoBackupReconciler, client.Client) {
	t.Helper()
	scheme := runtime.NewScheme()
	if err := clientgoscheme.AddToScheme(scheme); err != nil {
		t.Fatal(err)
	}
	if err := dojov1alpha1.AddToScheme(scheme); err != nil {
		t.Fatal(err)
	}
	c := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(objs...).
		// Mimic the real /status endpoints: both our CRD and Jobs have one, so
		// status writes must go through Status().Update() — plain Update()
		// silently drops status changes for these types, here AND in real life.
		WithStatusSubresource(&dojov1alpha1.DojoBackup{}, &batchv1.Job{}).
		Build()
	return &DojoBackupReconciler{
		Client:   c,
		Scheme:   scheme,
		Recorder: record.NewFakeRecorder(32), // buffers events instead of sending them
	}, c
}

func sampleBackup() *dojov1alpha1.DojoBackup {
	return &dojov1alpha1.DojoBackup{
		ObjectMeta: metav1.ObjectMeta{Name: "dojo-db", Namespace: "devops-dojo"},
		Spec: dojov1alpha1.DojoBackupSpec{
			Schedule:  "*/5 * * * *",
			Retention: 3,
			Database: dojov1alpha1.DatabaseRef{
				Host: "db", Name: "dojo", User: "dojo",
				PasswordSecret: dojov1alpha1.SecretKeyRef{Name: "dojo-secrets", Key: "POSTGRES_PASSWORD"},
			},
		},
	}
}

// reconcileTwice runs Reconcile twice: once to add the finalizer (which
// returns early by design) and once to do the real work — mirroring how the
// controller actually behaves after an Update re-triggers it.
func reconcileTwice(t *testing.T, r *DojoBackupReconciler, name types.NamespacedName) {
	t.Helper()
	for i := 0; i < 2; i++ {
		if _, err := r.Reconcile(context.Background(), ctrl.Request{NamespacedName: name}); err != nil {
			t.Fatalf("reconcile %d: %v", i+1, err)
		}
	}
}

func TestReconcileCreatesCronJobAndPVC(t *testing.T) {
	backup := sampleBackup()
	r, c := newTestReconciler(t, backup)
	name := types.NamespacedName{Name: "dojo-db", Namespace: "devops-dojo"}

	reconcileTwice(t, r, name)

	// The CronJob exists, carries the schedule, and is owned by the CR
	// (ownership = garbage collection + event routing).
	cj := &batchv1.CronJob{}
	if err := c.Get(context.Background(), types.NamespacedName{Name: "dojo-db-backup", Namespace: "devops-dojo"}, cj); err != nil {
		t.Fatalf("expected CronJob to exist: %v", err)
	}
	if cj.Spec.Schedule != "*/5 * * * *" {
		t.Errorf("schedule = %q, want */5 * * * *", cj.Spec.Schedule)
	}
	if len(cj.OwnerReferences) != 1 || cj.OwnerReferences[0].Kind != "DojoBackup" {
		t.Errorf("CronJob not owned by DojoBackup: %+v", cj.OwnerReferences)
	}
	if cj.Spec.ConcurrencyPolicy != batchv1.ForbidConcurrent {
		t.Errorf("concurrencyPolicy = %v, want Forbid", cj.Spec.ConcurrencyPolicy)
	}

	// The PVC exists with the default 1Gi.
	pvc := &corev1.PersistentVolumeClaim{}
	if err := c.Get(context.Background(), types.NamespacedName{Name: "dojo-db-backups", Namespace: "devops-dojo"}, pvc); err != nil {
		t.Fatalf("expected PVC to exist: %v", err)
	}
	if got := pvc.Spec.Resources.Requests.Storage().String(); got != "1Gi" {
		t.Errorf("PVC size = %s, want 1Gi", got)
	}

	// Status was published through the subresource: Ready=True.
	got := &dojov1alpha1.DojoBackup{}
	if err := c.Get(context.Background(), name, got); err != nil {
		t.Fatal(err)
	}
	if !meta.IsStatusConditionTrue(got.Status.Conditions, "Ready") {
		t.Errorf("Ready condition not True: %+v", got.Status.Conditions)
	}
	if !controllerutil.ContainsFinalizer(got, finalizerName) {
		t.Error("finalizer missing after reconcile")
	}
}

// The defining property of level-based reconciliation: reconcile UPDATES
// drifted children back to spec instead of erroring or duplicating them.
func TestReconcileConvergesDriftedCronJob(t *testing.T) {
	backup := sampleBackup()
	r, c := newTestReconciler(t, backup)
	name := types.NamespacedName{Name: "dojo-db", Namespace: "devops-dojo"}
	reconcileTwice(t, r, name)

	// Simulate an out-of-band edit ("someone kubectl-edited the CronJob").
	cj := &batchv1.CronJob{}
	cjName := types.NamespacedName{Name: "dojo-db-backup", Namespace: "devops-dojo"}
	if err := c.Get(context.Background(), cjName, cj); err != nil {
		t.Fatal(err)
	}
	cj.Spec.Schedule = "0 0 1 1 *" // tampered
	if err := c.Update(context.Background(), cj); err != nil {
		t.Fatal(err)
	}

	if _, err := r.Reconcile(context.Background(), ctrl.Request{NamespacedName: name}); err != nil {
		t.Fatal(err)
	}
	if err := c.Get(context.Background(), cjName, cj); err != nil {
		t.Fatal(err)
	}
	if cj.Spec.Schedule != "*/5 * * * *" {
		t.Errorf("drift not converged: schedule = %q", cj.Spec.Schedule)
	}
}

// Suspend must propagate: pausing the CR pauses the CronJob without deleting
// anything (the lab 06 exercise extends this test).
func TestReconcilePropagatesSuspend(t *testing.T) {
	backup := sampleBackup()
	suspend := true
	backup.Spec.Suspend = &suspend
	r, c := newTestReconciler(t, backup)
	reconcileTwice(t, r, types.NamespacedName{Name: "dojo-db", Namespace: "devops-dojo"})

	cj := &batchv1.CronJob{}
	if err := c.Get(context.Background(), types.NamespacedName{Name: "dojo-db-backup", Namespace: "devops-dojo"}, cj); err != nil {
		t.Fatal(err)
	}
	if cj.Spec.Suspend == nil || !*cj.Spec.Suspend {
		t.Error("suspend=true not propagated to CronJob")
	}
}

// Deletion semantics: with an active Job the finalizer must hold the object;
// with no active Jobs it must be released.
func TestDeletionBlockedWhileJobRuns(t *testing.T) {
	backup := sampleBackup()
	r, c := newTestReconciler(t, backup)
	name := types.NamespacedName{Name: "dojo-db", Namespace: "devops-dojo"}
	reconcileTwice(t, r, name) // creates children + finalizer

	// A running Job owned by our CronJob. Status is set through the /status
	// subresource in a second step — exactly as the real job controller would.
	activeJob := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name: "dojo-db-backup-123", Namespace: "devops-dojo",
			OwnerReferences: []metav1.OwnerReference{{
				APIVersion: "batch/v1", Kind: "CronJob", Name: "dojo-db-backup", UID: "x",
			}},
		},
	}
	if err := c.Create(context.Background(), activeJob); err != nil {
		t.Fatal(err)
	}
	activeJob.Status.Active = 1
	if err := c.Status().Update(context.Background(), activeJob); err != nil {
		t.Fatal(err)
	}

	// Delete the CR: the fake client honors finalizers, so the object gains a
	// deletionTimestamp but is NOT removed.
	got := &dojov1alpha1.DojoBackup{}
	if err := c.Get(context.Background(), name, got); err != nil {
		t.Fatal(err)
	}
	if err := c.Delete(context.Background(), got); err != nil {
		t.Fatal(err)
	}

	if _, err := r.Reconcile(context.Background(), ctrl.Request{NamespacedName: name}); err != nil {
		t.Fatal(err)
	}
	if err := c.Get(context.Background(), name, got); err != nil {
		t.Fatalf("CR should still exist while job is active: %v", err)
	}
	if !controllerutil.ContainsFinalizer(got, finalizerName) {
		t.Fatal("finalizer removed while a job was still active")
	}

	// Job finishes → next reconcile releases the finalizer → object disappears.
	activeJob.Status.Active = 0
	now := metav1.Now()
	activeJob.Status.CompletionTime = &now
	if err := c.Status().Update(context.Background(), activeJob); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Reconcile(context.Background(), ctrl.Request{NamespacedName: name}); err != nil {
		t.Fatal(err)
	}
	err := c.Get(context.Background(), name, got)
	if err == nil {
		j := &batchv1.Job{}
		_ = c.Get(context.Background(), types.NamespacedName{Name: "dojo-db-backup-123", Namespace: "devops-dojo"}, j)
		t.Fatalf("CR still exists after finalizer should have been removed: finalizers=%v deletionTs=%v jobActive=%d",
			got.Finalizers, got.DeletionTimestamp, j.Status.Active)
	}
}
