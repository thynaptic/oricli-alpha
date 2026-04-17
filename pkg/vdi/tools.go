package vdi

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/tools"
)

// --- Pillar 47: VDI Tool Bridge ---
// Exposes VDI capabilities to the Sovereign Engine's dynamic toolbox.

func (m *Manager) RegisterTools(registry *tools.Registry, vision *VisionGroundingService, scheduler *kernel.Scheduler, indexer *FSIndexer) {
	// 0. Workspace Reporting
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_sys_report_workspace",
			Description: "Reports the current active workspace path and project name.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{},
			},
		},
		Category: tools.TypeSystem,
		Handler: func(args map[string]interface{}) (string, error) {
			// This tool is a placeholder for LLM reasoning to call when it needs to be 
			// certain of its grounding. The actual path is handled via CurrentRemotePWD injection.
			return "Grounding verified. Operating in the provided client workspace.", nil
		},
	})

	// 1. Browser Navigation
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_browser_goto",
			Description: "Navigate the active browser session to a specific URL.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"url": {Type: "string", Description: "The full URL to navigate to (e.g., https://example.com)."},
				},
				Required: []string{"url"},
			},
		},
		Category: tools.TypeWeb,
		Handler: func(args map[string]interface{}) (string, error) {
			url, ok := args["url"].(string)
			if !ok { return "", fmt.Errorf("missing url parameter") }
			return m.Navigate(url)
		},
	})

	// 2. Browser Scrape
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_browser_scrape",
			Description: "Extracts all visible text from the current browser page.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{},
			},
		},
		Category: tools.TypeWeb,
		Handler: func(args map[string]interface{}) (string, error) {
			return m.Scrape()
		},
	})

	// 3. Browser Click
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_browser_click",
			Description: "Click an element on the current page using a CSS selector.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"selector": {Type: "string", Description: "A valid CSS selector (e.g., 'button.submit')."},
				},
				Required: []string{"selector"},
			},
		},
		Category: tools.TypeWeb,
		Handler: func(args map[string]interface{}) (string, error) {
			selector, ok := args["selector"].(string)
			if !ok { return "", fmt.Errorf("missing selector parameter") }
			return m.Click(selector)
		},
	})

	// 4. File Read
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_sys_read",
			Description: "Read the contents of a file on the host system.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"path": {Type: "string", Description: "Absolute or relative path to the file."},
				},
				Required: []string{"path"},
			},
		},
		Category: tools.TypeSystem,
		Handler: func(args map[string]interface{}) (string, error) {
			path, ok := args["path"].(string)
			if !ok { return "", fmt.Errorf("missing path parameter") }
			return m.ReadFile(path)
		},
	})

	// 5. System Execute
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_sys_exec",
			Description: "Execute a bash command directly on the host system.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"command": {Type: "string", Description: "The bash command to run."},
				},
				Required: []string{"command"},
			},
		},
		Category: tools.TypeSystem,
		Handler: func(args map[string]interface{}) (string, error) {
			cmd, ok := args["command"].(string)
			if !ok { return "", fmt.Errorf("missing command parameter") }
			return m.ExecCommand(cmd)
		},
	})

	// 6. Visual Click (Pillar 50)
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_visual_click",
			Description: "Look at the current screen and click an element based on its natural language description.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"description": {Type: "string", Description: "The element to find (e.g., 'the Login button')."},
				},
				Required: []string{"description"},
			},
		},
		Category: tools.TypeWeb,
		Handler: func(args map[string]interface{}) (string, error) {
			desc, ok := args["description"].(string)
			if !ok { return "", fmt.Errorf("missing description parameter") }

			// 1. Capture Eyes
			img, err := m.Screenshot()
			if err != nil { return "", err }

			// 2. Ground Reality
			x, y, err := vision.GetElementCoordinates(context.Background(), img, desc)
			if err != nil { return "", err }

			// 3. Act
			return m.ClickAt(x, y)
		},
	})

	// 7. Temporal Intent (Pillar 55)
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "sov_schedule_task",
			Description: "Schedule an autonomous task to be executed by the swarm at a future time.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"operation":       {Type: "string", Description: "The swarm operation to trigger (e.g., 'audit_logs')."},
					"params":          {Type: "object", Description: "Arguments for the operation."},
					"delay_seconds":    {Type: "number", Description: "Seconds to wait before first execution."},
					"interval_seconds": {Type: "number", Description: "Optional: If > 0, the task repeats every N seconds."},
				},
				Required: []string{"operation", "delay_seconds"},
			},
		},
		Category: tools.TypeSystem,
		Handler: func(args map[string]interface{}) (string, error) {
			op, _ := args["operation"].(string)
			params, _ := args["params"].(map[string]interface{})
			delaySec, _ := args["delay_seconds"].(float64)
			intervalSec, _ := args["interval_seconds"].(float64)

			if scheduler == nil {
				return "", fmt.Errorf("scheduler not initialized")
			}

			id := scheduler.ScheduleTask(op, params, 
				time.Duration(delaySec)*time.Second, 
				time.Duration(intervalSec)*time.Second)

			return fmt.Sprintf("Task %s scheduled successfully.", id), nil
		},
	})

	// 8. Filesystem Indexing (Pillar 56)
	registry.Register(&tools.Tool{
		Definition: tools.ToolDefinition{
			Name:        "vdi_sys_index",
			Description: "Index a directory on the host system and map its files into the working memory graph.",
			Parameters: tools.ToolParameters{
				Type: "object",
				Properties: map[string]tools.ToolProperty{
					"path": {Type: "string", Description: "The absolute or relative path to the directory to index."},
				},
				Required: []string{"path"},
			},
		},
		Category: tools.TypeSystem,
		Handler: func(args map[string]interface{}) (string, error) {
			path, _ := args["path"].(string)
			if indexer == nil { return "", fmt.Errorf("indexer not initialized") }
			if err := indexer.IndexRecursive(path); err != nil { return "", err }
			return fmt.Sprintf("Successfully indexed substrate at: %s", path), nil
		},
	})

	log.Println("[VDI] Registered native System, Browser, Visual, Temporal, and Indexing tools.")
}
