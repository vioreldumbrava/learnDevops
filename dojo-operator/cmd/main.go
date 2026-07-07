// The operator's entrypoint. All it does is configure and start a MANAGER —
// controller-runtime's runtime harness that owns everything the reconciler
// needs but shouldn't build itself:
//
//   - a shared informer CACHE (watches the API server once, serves all reads
//     locally — this is why controllers scale to thousands of objects),
//   - the work queue + retry/backoff around Reconcile,
//   - a /metrics endpoint (Prometheus — same pillar as lab 10),
//   - /healthz & /readyz probes (lab 08, now on the other side of the fence),
//   - optional leader election, so two replicas don't reconcile twice.
package main

import (
	"flag"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"

	dojov1alpha1 "github.com/devops-dojo/dojo-operator/api/v1alpha1"
	"github.com/devops-dojo/dojo-operator/internal/controller"
)

func main() {
	var metricsAddr, probeAddr string
	var enableLeaderElection bool
	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080", "metrics endpoint (Prometheus scrapes this)")
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081", "liveness/readiness endpoint")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false,
		"enable when running >1 replica so only one reconciles at a time")
	opts := zap.Options{Development: true} // human-readable logs; drop for JSON in prod
	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))
	setupLog := ctrl.Log.WithName("setup")

	// The scheme maps Go types <-> API kinds. Built-ins (Pods, CronJobs…)
	// come from client-go; our CRD types register themselves on top.
	scheme := runtime.NewScheme()
	if err := clientgoscheme.AddToScheme(scheme); err != nil {
		setupLog.Error(err, "adding client-go types to scheme")
		os.Exit(1)
	}
	if err := dojov1alpha1.AddToScheme(scheme); err != nil {
		setupLog.Error(err, "adding dojo.dev types to scheme")
		os.Exit(1)
	}

	// GetConfigOrDie resolves credentials the same way kubectl does:
	// in-cluster ServiceAccount token when deployed (lab 05), your local
	// kubeconfig when running `go run ./cmd` against kind (lab 02).
	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		Metrics:                metricsserver.Options{BindAddress: metricsAddr},
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         enableLeaderElection,
		LeaderElectionID:       "dojobackup.dojo.dev",
	})
	if err != nil {
		setupLog.Error(err, "unable to create manager")
		os.Exit(1)
	}

	if err := (&controller.DojoBackupReconciler{
		Client:   mgr.GetClient(),
		Scheme:   mgr.GetScheme(),
		Recorder: mgr.GetEventRecorderFor("dojo-operator"),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to set up DojoBackup controller")
		os.Exit(1)
	}

	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	// Start blocks: it syncs the cache, starts the workers, and runs until
	// SIGTERM — at which point in-flight Reconciles finish (graceful shutdown).
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "manager exited with error")
		os.Exit(1)
	}
}
