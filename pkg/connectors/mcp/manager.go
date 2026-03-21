package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

// --- Pillar 41: MCP Manager ---
// Orchestrates multiple MCP server connections and manages their lifecycles.

type MCPConfig struct {
	Servers map[string]ServerConfig `json:"mcpServers"`
}

type ServerConfig struct {
	Command string   `json:"command"`
	Args    []string `json:"args"`
	Enabled *bool    `json:"enabled,omitempty"` // nil = enabled by default
}

type MCPManager struct {
	Clients map[string]*Client
	Config  MCPConfig
	mu      sync.RWMutex
}

func NewMCPManager(configPath string) *MCPManager {
	m := &MCPManager{
		Clients: make(map[string]*Client),
	}
	if err := m.LoadConfig(configPath); err != nil {
		log.Printf("[MCPManager] Warning: Failed to load config from %s: %v", configPath, err)
	}
	return m
}

func (m *MCPManager) LoadConfig(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &m.Config)
}

// StartAll connects to all configured MCP servers concurrently.
// Each server gets its own timeout (perServerTimeout) to allow for first-time
// npm downloads. Servers are started in parallel so one slow download never
// blocks the others.
func (m *MCPManager) StartAll(ctx context.Context) error {
	const perServerTimeout = 120 * time.Second

	var wg sync.WaitGroup
	for name, cfg := range m.Config.Servers {
		if cfg.Enabled != nil && !*cfg.Enabled {
			log.Printf("[MCPManager] Skipping disabled server: %s", name)
			continue
		}

		wg.Add(1)
		go func(name string, cfg ServerConfig) {
			defer wg.Done()
			log.Printf("[MCPManager] Connecting to server: %s...", name)
			client := NewClient(cfg.Command, cfg.Args)
			if err := client.Start(); err != nil {
				log.Printf("[MCPManager] Error starting %s: %v", name, err)
				return
			}

			initCtx, cancel := context.WithTimeout(ctx, perServerTimeout)
			defer cancel()
			_, err := client.Initialize(initCtx)
			if err != nil {
				log.Printf("[MCPManager] Failed to initialize %s: %v", name, err)
				client.Stop()
				return
			}

			m.mu.Lock()
			m.Clients[name] = client
			m.mu.Unlock()
			log.Printf("[MCPManager] Server %s initialized successfully.", name)
		}(name, cfg)
	}
	wg.Wait()
	return nil
}

func (m *MCPManager) StopAll() {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, client := range m.Clients {
		client.Stop()
	}
}

// ListAllTools aggregates tools from all connected servers.
func (m *MCPManager) ListAllTools(ctx context.Context) (map[string][]MCPTool, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	results := make(map[string][]MCPTool)
	for name, client := range m.Clients {
		tools, err := client.ListTools(ctx)
		if err != nil {
			log.Printf("[MCPManager] Error listing tools for %s: %v", name, err)
			continue
		}
		results[name] = tools
	}
	return results, nil
}

// CallTool routes a tool call to the appropriate MCP server.
func (m *MCPManager) CallTool(ctx context.Context, serverName, toolName string, args map[string]interface{}) (*CallToolResult, error) {
	m.mu.RLock()
	client, ok := m.Clients[serverName]
	m.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("MCP server not found: %s", serverName)
	}

	return client.CallTool(ctx, toolName, args)
}
