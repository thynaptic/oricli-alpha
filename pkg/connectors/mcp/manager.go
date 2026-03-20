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

// StartAll connects to all configured MCP servers and performs handshakes.
func (m *MCPManager) StartAll(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for name, cfg := range m.Config.Servers {
		log.Printf("[MCPManager] Connecting to server: %s...", name)
		client := NewClient(cfg.Command, cfg.Args)
		if err := client.Start(); err != nil {
			log.Printf("[MCPManager] Error starting %s: %v", name, err)
			continue
		}

		// Perform handshake
		initCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
		_, err := client.Initialize(initCtx)
		cancel()
		if err != nil {
			log.Printf("[MCPManager] Failed to initialize %s: %v", name, err)
			client.Stop()
			continue
		}

		m.Clients[name] = client
		log.Printf("[MCPManager] Server %s initialized successfully.", name)
	}
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
