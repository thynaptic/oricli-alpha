package service

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	rpc "github.com/thynaptic/oricli-go/pkg/rpc"
)

// ModuleMetadata represents the metadata for a brain module
type ModuleMetadata struct {
	Name        string            `json:"name"`
	Version     string            `json:"version"`
	Description string            `json:"description"`
	Author      string            `json:"author"`
	Operations  []string          `json:"operations"`
	Inputs      map[string]string `json:"inputs"`
	Outputs     map[string]string `json:"outputs"`
	IsGoNative  bool              `json:"is_go_native"`
}

// ModuleInstance represents an active module instance
type ModuleInstance interface {
	Initialize(ctx context.Context) error
	Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error)
	Metadata() ModuleMetadata
	Cleanup(ctx context.Context) error
}

// ModuleRegistry manages module discovery and instances
type ModuleRegistry struct {
	modules    map[string]ModuleMetadata
	instances  map[string]ModuleInstance
	mu         sync.RWMutex
	discovered bool
	modulesDir string
}

// NewModuleRegistry creates a new module registry
func NewModuleRegistry(modulesDir string) *ModuleRegistry {
	return &ModuleRegistry{
		modules:    make(map[string]ModuleMetadata),
		instances:  make(map[string]ModuleInstance),
		modulesDir: modulesDir,
	}
}

// RegisterNativeModule manually registers a module
func (r *ModuleRegistry) RegisterNativeModule(name string, instance ModuleInstance) {
	r.mu.Lock()
	defer r.mu.Unlock()

	metadata := instance.Metadata()
	r.modules[name] = metadata
	r.instances[name] = instance
}

// DiscoverModules finds modules in the specified directory
func (r *ModuleRegistry) DiscoverModules(ctx context.Context) (int, int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if r.discovered {
		return len(r.modules), 0, nil
	}

	r.discovered = true
	return len(r.modules), 0, nil
}

// GetModule returns a module instance by name
func (r *ModuleRegistry) GetModule(name string) (ModuleInstance, error) {
	r.mu.RLock()
	instance, ok := r.instances[name]
	r.mu.RUnlock()

	if ok {
		return instance, nil
	}

	return nil, fmt.Errorf("module %s not found", name)
}

// ListModules returns a list of registered module names
func (r *ModuleRegistry) ListModules() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	names := make([]string, 0, len(r.modules))
	for name := range r.modules {
		names = append(names, name)
	}
	return names
}

// GetMetadata returns metadata for a module
func (r *ModuleRegistry) GetMetadata(name string) (ModuleMetadata, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	meta, ok := r.modules[name]
	return meta, ok
}

// PythonModuleProxy is a Go wrapper for a Python module managed via gRPC
type PythonModuleProxy struct {
	ModuleMetadata ModuleMetadata
	Client         rpc.ModuleServiceClient
}

func (p *PythonModuleProxy) Initialize(ctx context.Context) error {
	// Ping health check to ensure worker is alive for this module
	_, err := p.Client.HealthCheck(ctx, &rpc.HealthCheckRequest{})
	return err
}

func (p *PythonModuleProxy) Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error) {
	paramsJSON, err := json.Marshal(params)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	req := &rpc.ExecuteRequest{
		TaskId:     fmt.Sprintf("go_proxy_%d", time.Now().UnixNano()),
		ModuleName: p.ModuleMetadata.Name,
		Operation:  operation,
		ParamsJson: string(paramsJSON),
	}

	resp, err := p.Client.ExecuteOperation(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("gRPC execution failed: %w", err)
	}

	if !resp.Success {
		return nil, fmt.Errorf("python module error: %s", resp.ErrorMessage)
	}

	var result interface{}
	err = json.Unmarshal([]byte(resp.ResultJson), &result)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal result: %w", err)
	}

	return result, nil
}

func (p *PythonModuleProxy) Metadata() ModuleMetadata {
	return p.ModuleMetadata
}

func (p *PythonModuleProxy) Cleanup(ctx context.Context) error {
	return nil
}
