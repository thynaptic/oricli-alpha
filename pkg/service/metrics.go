package service

import (
	"sync"
	"time"
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
