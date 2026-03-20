package vdi

import (
	"context"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/tools"
)

// --- Pillar 47: VDI Tool Bridge ---
// Exposes VDI capabilities to the Sovereign Engine's dynamic toolbox.

func (m *Manager) RegisterTools(registry *tools.Registry, vision *VisionGroundingService) {
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

	log.Println("[VDI] Registered native System, Browser, and Visual tools to Sovereign Toolbox.")
}
