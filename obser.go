package observability

import (
	"encoding/json"
	"net/http"
	"os"
	"runtime"
	"time"
)

var startTime = time.Now()

type HealthStatus struct {
	Status    string            `json:"status"`
	Uptime    string            `json:"uptime"`
	GoVersion string            `json:"go_version"`
	Hostname  string            `json:"hostname,omitempty"`
	Checks    map[string]string `json:"checks,omitempty"`
}

type CheckFunc struct {
	Name  string
	Check func() error
}


func HealthHandler(checks ...CheckFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		hostname, _ := os.Hostname()

		results := make(map[string]string, len(checks))
		overall := "ok"

		for _, c := range checks {
			if err := c.Check(); err != nil {
				results[c.Name] = "fail: " + err.Error()
				overall = "degraded"
			} else {
				results[c.Name] = "ok"
			}
		}

		status := HealthStatus{
			Status:    overall,
			Uptime:    time.Since(startTime).Round(time.Second).String(),
			GoVersion: runtime.Version(),
			Hostname:  hostname,
			Checks:    results,
		}

		code := http.StatusOK
		if overall != "ok" {
			code = http.StatusServiceUnavailable
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(code)
		_ = json.NewEncoder(w).Encode(status)
	}
}

// RegisterRoutes mounts /healthz (and an alias /health) on the given mux.
// Pass nil to use http.DefaultServeMux.
//
//	observability.RegisterRoutes(nil, checks...)
//	observability.RegisterRoutes(myMux, checks...)
func RegisterRoutes(mux *http.ServeMux, checks ...CheckFunc) {
	if mux == nil {
		mux = http.DefaultServeMux
	}
	h := HealthHandler(checks...)
	mux.Handle("/healthz", h)
	mux.Handle("/health", h)
}
