// Package v1alpha1 defines the DojoBackup API — the "data half" of the operator.
//
// Every Kubernetes resource lives in a GROUP/VERSION (apps/v1, batch/v1 …).
// Ours is dojo.dev/v1alpha1: "dojo.dev" is the API group (a DNS name you own,
// so groups never collide), "v1alpha1" signals the schema may still change.
package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

var (
	// GroupVersion identifies this API group/version to the runtime scheme.
	GroupVersion = schema.GroupVersion{Group: "dojo.dev", Version: "v1alpha1"}

	// SchemeBuilder / AddToScheme register our Go types under that group/version
	// so client-go can convert between Go structs and the JSON the API server
	// speaks. Forgetting this registration is the classic
	// "no kind is registered for the type" error.
	SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}
	AddToScheme   = SchemeBuilder.AddToScheme
)
