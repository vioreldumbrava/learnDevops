package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// A DojoBackup says: "keep scheduled pg_dump backups of this database, retain
// the newest N". The USER writes spec (desired state); the CONTROLLER writes
// status (observed state). That split is the core Kubernetes contract, and it
// is why spec and status are separate structs with separate update endpoints.

// DatabaseRef points the backup at a Postgres instance. The password is NOT
// stored here — only a reference to a Secret key. The operator itself never
// reads the Secret; it wires the reference into the backup pod, so the
// operator's RBAC needs no access to secrets at all (least privilege, lab 27).
type DatabaseRef struct {
	// Host of the Postgres service, e.g. "db" (same-namespace Service name).
	Host string `json:"host"`
	// Port Postgres listens on.
	// +kubebuilder:default=5432
	Port int32 `json:"port,omitempty"`
	// Name of the database to dump, e.g. "dojo".
	Name string `json:"name"`
	// User to connect as, e.g. "dojo".
	User string `json:"user"`
	// PasswordSecret references the Secret KEY holding the password,
	// e.g. {name: dojo-secrets, key: POSTGRES_PASSWORD}.
	PasswordSecret SecretKeyRef `json:"passwordSecret"`
}

// SecretKeyRef names one key inside one Secret (same namespace as the CR).
type SecretKeyRef struct {
	Name string `json:"name"`
	Key  string `json:"key"`
}

// DojoBackupSpec is the desired state — what the user asks for.
type DojoBackupSpec struct {
	// Schedule in cron format, e.g. "*/5 * * * *" or "0 3 * * *".
	// The controller compiles this into a CronJob's schedule.
	Schedule string `json:"schedule"`

	// Database to back up.
	Database DatabaseRef `json:"database"`

	// Retention: keep the newest N dump files; older ones are pruned after
	// each successful backup.
	// +kubebuilder:default=5
	Retention int32 `json:"retention,omitempty"`

	// StorageSize for the PersistentVolumeClaim that holds the dumps,
	// e.g. "1Gi".
	// +kubebuilder:default="1Gi"
	StorageSize string `json:"storageSize,omitempty"`

	// Suspend pauses the schedule without deleting anything (propagated to
	// the CronJob). Same idea as `kubectl rollout pause`.
	Suspend *bool `json:"suspend,omitempty"`
}

// DojoBackupStatus is the observed state — what the controller found out.
// Users must never edit it; that's why the CRD enables the /status
// subresource, which makes the API server reject spec+status mixed writes.
type DojoBackupStatus struct {
	// Conditions follow the standard Kubernetes pattern (type/status/reason/
	// message/lastTransitionTime). "Ready" = the CronJob exists and matches
	// the spec. `kubectl wait --for=condition=Ready dojobackup/x` works off this.
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// ActiveJobs = backup Jobs currently running.
	ActiveJobs int32 `json:"activeJobs,omitempty"`

	// LastScheduleTime = when the CronJob last fired (mirrored for kubectl get).
	LastScheduleTime *metav1.Time `json:"lastScheduleTime,omitempty"`

	// LastSuccessfulTime = when a backup Job last completed successfully.
	LastSuccessfulTime *metav1.Time `json:"lastSuccessfulTime,omitempty"`

	// ObservedGeneration = the .metadata.generation the controller last acted
	// on. If observedGeneration < generation, the status is stale — a standard
	// trick consumers use to avoid trusting outdated conditions.
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`
}

// DojoBackup is the resource itself. The kubebuilder markers below are what
// `controller-gen` reads to produce the CRD YAML in config/crd/ — we commit
// that YAML so the labs work without the generator installed.
//
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=djb
// +kubebuilder:printcolumn:name="Schedule",type=string,JSONPath=`.spec.schedule`
// +kubebuilder:printcolumn:name="Ready",type=string,JSONPath=`.status.conditions[?(@.type=="Ready")].status`
// +kubebuilder:printcolumn:name="LastSuccess",type=date,JSONPath=`.status.lastSuccessfulTime`
type DojoBackup struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   DojoBackupSpec   `json:"spec,omitempty"`
	Status DojoBackupStatus `json:"status,omitempty"`
}

// DojoBackupList is required boilerplate: LIST responses are a distinct kind.
//
// +kubebuilder:object:root=true
type DojoBackupList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []DojoBackup `json:"items"`
}

func init() {
	SchemeBuilder.Register(&DojoBackup{}, &DojoBackupList{})
}
