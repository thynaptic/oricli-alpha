package service

import (
	"context"
	"fmt"
	"sync"
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

// RegisterNativeModule manually registers a Go-native module
func (r *ModuleRegistry) RegisterNativeModule(name string, instance ModuleInstance) {
	r.mu.Lock()
	defer r.mu.Unlock()

	metadata := instance.Metadata()
	metadata.IsGoNative = true
	r.modules[name] = metadata
	r.instances[name] = instance
}

// DiscoverModules finds modules in the specified directory
// For now, this mostly serves to store metadata that might be provided by the Python sidecar
func (r *ModuleRegistry) DiscoverModules(ctx context.Context) (int, int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if r.discovered {
		return len(r.modules), 0, nil
	}

	// In a real scenario, we might scan the Python modules directory to extract metadata
	// or wait for the Python sidecar to register its modules over gRPC.
	// For this migration, we'll assume Go owns the registry and Python modules 
	// are "proxied" via a Go instance that talks to the Python gRPC worker.

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
	Client         interface{} // placeholder for gRPC client
}

func (p *PythonModuleProxy) Initialize(ctx context.Context) error {
	return nil
}

func (p *PythonModuleProxy) Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error) {
	// Implement gRPC call to Python sidecar here
	return nil, fmt.Errorf("not implemented: python proxy execution")
}

func (p *PythonModuleProxy) Metadata() ModuleMetadata {
	return p.ModuleMetadata
}

func (p *PythonModuleProxy) Cleanup(ctx context.Context) error {
	return nil
}
