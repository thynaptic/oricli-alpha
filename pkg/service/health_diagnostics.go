package service

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// ModuleHealthInfo represents the health of a single module
type ModuleHealthInfo struct {
	Name          string                 `json:"name"`
	IsGoNative    bool                   `json:"is_go_native"`
	Status        ModuleState            `json:"status"`
	ImportTime    time.Duration          `json:"import_time"`
	LastCheck     time.Time              `json:"last_check"`
	Error         string                 `json:"error,omitempty"`
	ModuleClasses []string               `json:"module_classes,omitempty"`
	Details       map[string]interface{} `json:"details,omitempty"`
}

// ModuleHealthDiagnosticsService provides diagnostics for all modules
type ModuleHealthDiagnosticsService struct {
	registry *ModuleRegistry
	monitor  *ModuleMonitorService
	mu       sync.RWMutex
}

// NewModuleHealthDiagnosticsService creates a new diagnostics service
func NewModuleHealthDiagnosticsService(registry *ModuleRegistry, monitor *ModuleMonitorService) *ModuleHealthDiagnosticsService {
	return &ModuleHealthDiagnosticsService{
		registry: registry,
		monitor:  monitor,
	}
}

// ScanAllModules performs a comprehensive health scan
func (s *ModuleHealthDiagnosticsService) ScanAllModules(ctx context.Context) (map[string]ModuleHealthInfo, error) {
	results := make(map[string]ModuleHealthInfo)
	
	// 1. Scan Go Native Modules
	moduleNames := s.registry.ListModules()
	for _, name := range moduleNames {
		meta, _ := s.registry.GetMetadata(name)
		status, _ := s.monitor.GetModuleStatus(name)
		
		results[name] = ModuleHealthInfo{
			Name:       name,
			IsGoNative: meta.IsGoNative,
			Status:     status.State,
			LastCheck:  status.LastCheck,
			Error:      status.DegradationReason,
		}
	}

	// 2. Scan Python modules directory for "importability"
	// This part might trigger a call to the Python worker's diagnostics module
	
	return results, nil
}

// GetModuleHealth returns health info for a specific module
func (s *ModuleHealthDiagnosticsService) GetModuleHealth(name string) (ModuleHealthInfo, error) {
	meta, ok := s.registry.GetMetadata(name)
	if !ok {
		return ModuleHealthInfo{}, fmt.Errorf("module %s not found", name)
	}
	
	status, _ := s.monitor.GetModuleStatus(name)
	
	return ModuleHealthInfo{
		Name:       name,
		IsGoNative: meta.IsGoNative,
		Status:     status.State,
		LastCheck:  status.LastCheck,
		Error:      status.DegradationReason,
	}, nil
}
