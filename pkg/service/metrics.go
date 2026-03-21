package service

import (
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// OperationMetrics tracks metrics for a single operation
type OperationMetrics struct {
	Operation         string        `json:"operation"`
	CallCount         int64         `json:"call_count"`
	TotalTime         time.Duration `json:"total_time"`
	SuccessCount      int64         `json:"success_count"`
	FailureCount      int64         `json:"failure_count"`
	MinTime           time.Duration `json:"min_time"`
	MaxTime           time.Duration `json:"max_time"`
	LastCallTime      time.Time     `json:"last_call_time"`
	Errors            []string      `json:"errors"`
}

// ModuleMetrics tracks metrics for a module
type ModuleMetrics struct {
	ModuleName   string                       `json:"module_name"`
	Operations   map[string]*OperationMetrics `json:"operations"`
	TotalCalls   int64                        `json:"total_calls"`
	TotalTime    time.Duration                `json:"total_time"`
	LastActivity time.Time                    `json:"last_activity"`
}

// MetricsCollector collects and aggregates metrics
type MetricsCollector struct {
	metrics map[string]*ModuleMetrics
	mu      sync.RWMutex
}

// NewMetricsCollector creates a new metrics collector
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		metrics: make(map[string]*ModuleMetrics),
	}
}

// RecordOperation records an operation execution
func (c *MetricsCollector) RecordOperation(moduleName, operation string, duration time.Duration, success bool, err string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	m, ok := c.metrics[moduleName]
	if !ok {
		m = &ModuleMetrics{
			ModuleName: moduleName,
			Operations: make(map[string]*OperationMetrics),
		}
		c.metrics[moduleName] = m
	}

	op, ok := m.Operations[operation]
	if !ok {
		op = &OperationMetrics{
			Operation: operation,
			MinTime:   duration,
			MaxTime:   duration,
		}
		m.Operations[operation] = op
	}

	op.CallCount++
	op.TotalTime += duration
	op.LastCallTime = time.Now()

	if success {
		op.SuccessCount++
	} else {
		op.FailureCount++
		if err != "" {
			op.Errors = append(op.Errors, err)
			if len(op.Errors) > 10 {
				op.Errors = op.Errors[1:]
			}
		}
	}

	if duration < op.MinTime {
		op.MinTime = duration
	}
	if duration > op.MaxTime {
		op.MaxTime = duration
	}

	m.TotalCalls++
	m.TotalTime += duration
	m.LastActivity = time.Now()
}

// GetModuleMetrics returns metrics for a module
func (c *MetricsCollector) GetModuleMetrics(name string) *ModuleMetrics {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.metrics[name]
}

// GetAllMetrics returns all collected metrics
func (c *MetricsCollector) GetAllMetrics() map[string]*ModuleMetrics {
	c.mu.RLock()
	defer c.mu.RUnlock()
	
	// Return a copy
	res := make(map[string]*ModuleMetrics)
	for k, v := range c.metrics {
		res[k] = v
	}
	return res
}

// PrometheusHandler returns an http.Handler that exposes all collected metrics
// in Prometheus text exposition format. Wire to GET /metrics on the API server.
func (c *MetricsCollector) PrometheusHandler() http.Handler {
	registry := prometheus.NewRegistry()

	requestsTotal := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "oricli_requests_total",
		Help: "Total number of operations executed per module.",
	}, []string{"module", "operation"})

	requestsSucceeded := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "oricli_requests_succeeded_total",
		Help: "Total number of successful operations per module.",
	}, []string{"module", "operation"})

	requestsFailed := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "oricli_requests_failed_total",
		Help: "Total number of failed operations per module.",
	}, []string{"module", "operation"})

	requestDuration := prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Name: "oricli_request_duration_avg_seconds",
		Help: "Average operation duration in seconds per module.",
	}, []string{"module", "operation"})

	backboneInfo := prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Name: "oricli_backbone_info",
		Help: "Static info gauge for the Oricli backbone.",
	}, []string{"version"})

	registry.MustRegister(requestsTotal, requestsSucceeded, requestsFailed, requestDuration, backboneInfo)
	backboneInfo.WithLabelValues("v2").Set(1)

	// Snapshot current MetricsCollector state into Prometheus metrics on each scrape.
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		c.mu.RLock()
		for _, mod := range c.metrics {
			for _, op := range mod.Operations {
				labels := prometheus.Labels{"module": mod.ModuleName, "operation": op.Operation}
				requestsTotal.With(labels).Add(float64(op.CallCount))
				requestsSucceeded.With(labels).Add(float64(op.SuccessCount))
				requestsFailed.With(labels).Add(float64(op.FailureCount))
				if op.CallCount > 0 {
					avg := float64(op.TotalTime) / float64(op.CallCount) / float64(time.Second)
					requestDuration.With(labels).Set(avg)
				}
			}
		}
		c.mu.RUnlock()
		promhttp.HandlerFor(registry, promhttp.HandlerOpts{}).ServeHTTP(w, r)
	})
}
