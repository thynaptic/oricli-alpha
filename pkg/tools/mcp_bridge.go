package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/connectors/mcp"
)

// --- Pillar 42: MCP Tool Bridge ---
// Automatically bridges external MCP tools into Oricli's native toolbox.

func (r *Registry) RegisterMCPTools(ctx context.Context, manager *mcp.MCPManager) error {
	allTools, err := manager.ListAllTools(ctx)
	if err != nil {
		return err
	}

	for serverName, tools := range allTools {
		for _, t := range tools {
			// Convert MCPTool to native ToolDefinition
			var params ToolParameters
			_ = json.Unmarshal(t.InputSchema, &params)

			// Wrap tool call in a native handler
			handler := func(args map[string]interface{}) (string, error) {
				res, err := manager.CallTool(context.Background(), serverName, t.Name, args)
				if err != nil {
					return "", err
				}
				if res.IsError {
					return "", fmt.Errorf("MCP Tool Error: %v", res.Content)
				}
				
				// Aggregate text content
				var output string
				for _, c := range res.Content {
					if c.Type == "text" {
						output += c.Text + "\n"
					}
				}
				return output, nil
			}

			// Use prefixed name to avoid collisions
			nativeName := fmt.Sprintf("%s_%s", serverName, t.Name)
			
			r.Register(&Tool{
				Definition: ToolDefinition{
					Name:        nativeName,
					Description: fmt.Sprintf("[%s] %s", serverName, t.Description),
					Parameters:  params,
				},
				Handler:  handler,
				Category: TypeWeb, // Default to Web for MCP for now
			})
			
			log.Printf("[MCPBridge] Registered tool: %s", nativeName)
		}
	}

	return nil
}
