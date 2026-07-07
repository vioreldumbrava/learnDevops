// This file is normally produced by `controller-gen object` from the markers
// in dojobackup_types.go — we committed it (hand-written, same shape) so the
// project builds with nothing but Go. Why it must exist at all: client-go
// caches shared objects; every type served from the cache must be deep-copyable
// (runtime.Object requires DeepCopyObject), otherwise two controllers could
// mutate the same cached struct and corrupt each other.
//
// To regenerate instead of hand-maintaining (lab 06 exercise):
//   docker run --rm -v ${PWD}:/w -w /w golang:1.25 sh -c \
//     "go run sigs.k8s.io/controller-tools/cmd/controller-gen@v0.16.5 object paths=./api/..."

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	runtime "k8s.io/apimachinery/pkg/runtime"
)

// DeepCopyInto copies the receiver into out.
func (in *DatabaseRef) DeepCopyInto(out *DatabaseRef) {
	*out = *in
	out.PasswordSecret = in.PasswordSecret
}

// DeepCopy returns a deep copy of the receiver.
func (in *DatabaseRef) DeepCopy() *DatabaseRef {
	if in == nil {
		return nil
	}
	out := new(DatabaseRef)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies the receiver into out.
func (in *SecretKeyRef) DeepCopyInto(out *SecretKeyRef) {
	*out = *in
}

// DeepCopy returns a deep copy of the receiver.
func (in *SecretKeyRef) DeepCopy() *SecretKeyRef {
	if in == nil {
		return nil
	}
	out := new(SecretKeyRef)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies the receiver into out.
func (in *DojoBackupSpec) DeepCopyInto(out *DojoBackupSpec) {
	*out = *in
	in.Database.DeepCopyInto(&out.Database)
	if in.Suspend != nil {
		out.Suspend = new(bool)
		*out.Suspend = *in.Suspend
	}
}

// DeepCopy returns a deep copy of the receiver.
func (in *DojoBackupSpec) DeepCopy() *DojoBackupSpec {
	if in == nil {
		return nil
	}
	out := new(DojoBackupSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies the receiver into out.
func (in *DojoBackupStatus) DeepCopyInto(out *DojoBackupStatus) {
	*out = *in
	if in.Conditions != nil {
		out.Conditions = make([]metav1.Condition, len(in.Conditions))
		for i := range in.Conditions {
			in.Conditions[i].DeepCopyInto(&out.Conditions[i])
		}
	}
	if in.LastScheduleTime != nil {
		out.LastScheduleTime = in.LastScheduleTime.DeepCopy()
	}
	if in.LastSuccessfulTime != nil {
		out.LastSuccessfulTime = in.LastSuccessfulTime.DeepCopy()
	}
}

// DeepCopy returns a deep copy of the receiver.
func (in *DojoBackupStatus) DeepCopy() *DojoBackupStatus {
	if in == nil {
		return nil
	}
	out := new(DojoBackupStatus)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies the receiver into out.
func (in *DojoBackup) DeepCopyInto(out *DojoBackup) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	in.Status.DeepCopyInto(&out.Status)
}

// DeepCopy returns a deep copy of the receiver.
func (in *DojoBackup) DeepCopy() *DojoBackup {
	if in == nil {
		return nil
	}
	out := new(DojoBackup)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject makes DojoBackup satisfy runtime.Object.
func (in *DojoBackup) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto copies the receiver into out.
func (in *DojoBackupList) DeepCopyInto(out *DojoBackupList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		out.Items = make([]DojoBackup, len(in.Items))
		for i := range in.Items {
			in.Items[i].DeepCopyInto(&out.Items[i])
		}
	}
}

// DeepCopy returns a deep copy of the receiver.
func (in *DojoBackupList) DeepCopy() *DojoBackupList {
	if in == nil {
		return nil
	}
	out := new(DojoBackupList)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject makes DojoBackupList satisfy runtime.Object.
func (in *DojoBackupList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}
