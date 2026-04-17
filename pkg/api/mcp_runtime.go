package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	tenantauth "github.com/thynaptic/oricli-go/pkg/auth"
	coreauth "github.com/thynaptic/oricli-go/pkg/core/auth"
)

type mcpRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type mcpResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id,omitempty"`
	Result  interface{} `json:"result,omitempty"`
	Error   *mcpError   `json:"error,omitempty"`
}

type mcpError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type mcpTool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description,omitempty"`
	InputSchema map[string]interface{} `json:"inputSchema,omitempty"`
}

var runtimeMCPTools = []mcpTool{
	{
		Name:        "check_health",
		Description: "Check ORI runtime health.",
		InputSchema: map[string]interface{}{"type": "object", "properties": map[string]interface{}{}, "additionalProperties": false},
	},
	{
		Name:        "get_key_info",
		Description: "Return tenant, key id, and scopes for the authenticated key.",
		InputSchema: map[string]interface{}{"type": "object", "properties": map[string]interface{}{}, "additionalProperties": false},
	},
	{
		Name:        "get_capabilities",
		Description: "Return the ORI capability manifest.",
		InputSchema: map[string]interface{}{"type": "object", "properties": map[string]interface{}{}, "additionalProperties": false},
	},
	{
		Name:        "list_surfaces",
		Description: "Return valid ORI product surfaces and profile sets.",
		InputSchema: map[string]interface{}{"type": "object", "properties": map[string]interface{}{}, "additionalProperties": false},
	},
	{
		Name:        "list_working_styles",
		Description: "Return working style profiles for a given surface.",
		InputSchema: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"surface": map[string]interface{}{
					"type": "string",
					"enum": []string{"studio", "home", "dev", "red"},
				},
			},
			"required":             []string{"surface"},
			"additionalProperties": false,
		},
	},
	{
		Name:        "get_request_template",
		Description: "Return a request template from the developer portal request catalog.",
		InputSchema: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"template": map[string]interface{}{
					"type": "string",
				},
			},
			"required":             []string{"template"},
			"additionalProperties": false,
		},
	},
}

func (s *ServerV2) handleMCP(c *gin.Context) {
	var req mcpRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, mcpResponse{
			JSONRPC: "2.0",
			Error:   &mcpError{Code: -32700, Message: "invalid JSON-RPC request"},
		})
		return
	}

	switch req.Method {
	case "initialize":
		c.JSON(http.StatusOK, mcpResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"protocolVersion": "2025-03-26",
				"capabilities": map[string]interface{}{
					"tools": map[string]interface{}{},
				},
				"serverInfo": map[string]interface{}{
					"name":    "ori-runtime",
					"version": "2026-04-17",
				},
			},
		})
	case "tools/list":
		c.JSON(http.StatusOK, mcpResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"tools": runtimeMCPTools,
			},
		})
	case "tools/call":
		s.handleMCPToolCall(c, req)
	default:
		c.JSON(http.StatusOK, mcpResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &mcpError{Code: -32601, Message: "method not found"},
		})
	}
}

func (s *ServerV2) handleMCPToolCall(c *gin.Context, req mcpRequest) {
	var params struct {
		Name      string                 `json:"name"`
		Arguments map[string]interface{} `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		c.JSON(http.StatusOK, mcpResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &mcpError{Code: -32602, Message: "invalid tool call params"},
		})
		return
	}

	result, err := s.invokeMCPTool(c, params.Name, params.Arguments)
	if err != nil {
		c.JSON(http.StatusOK, mcpResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"content": []map[string]interface{}{
					{"type": "text", "text": err.Error()},
				},
				"isError": true,
			},
		})
		return
	}

	text := result
	if _, ok := result.(string); !ok {
		b, _ := json.Marshal(result)
		text = string(b)
	}
	c.JSON(http.StatusOK, mcpResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result: map[string]interface{}{
			"content": []map[string]interface{}{
				{"type": "text", "text": text},
			},
			"isError": false,
		},
	})
}

func (s *ServerV2) invokeMCPTool(c *gin.Context, name string, args map[string]interface{}) (interface{}, error) {
	ctx := c.Request.Context()

	switch name {
	case "check_health":
		return map[string]interface{}{
			"status":  "ready",
			"system":  "oricli-alpha-v2",
			"surface": c.GetHeader("X-Ori-Context"),
		}, nil
	case "get_key_info":
		return map[string]interface{}{
			"tenant_id": tenantauth.TenantID(ctx),
			"key_id":    coreauth.KeyID(ctx),
			"scopes":    coreauth.Scopes(ctx),
		}, nil
	case "get_capabilities":
		return loadJSONFile("dev-portal/capabilities.json")
	case "list_surfaces":
		agentDoc, err := loadJSONFile("dev-portal/agent.json")
		if err != nil {
			return nil, err
		}
		return pickMapKeys(agentDoc, "surfaces"), nil
	case "list_working_styles":
		surface, _ := args["surface"].(string)
		agentDoc, err := loadJSONFile("dev-portal/agent.json")
		if err != nil {
			return nil, err
		}
		surfaces := pickMapKeys(agentDoc, "surfaces")
		if entry, ok := surfaces[surface]; ok {
			return entry, nil
		}
		return map[string]interface{}{"surface": surface, "profiles": []string{}}, nil
	case "get_request_template":
		template, _ := args["template"].(string)
		reqDoc, err := loadJSONFile("dev-portal/requests.json")
		if err != nil {
			return nil, err
		}
		templates := pickMapKeys(reqDoc, "templates")
		if entry, ok := templates[template]; ok {
			return entry, nil
		}
		return map[string]interface{}{"error": "template not found", "template": template}, nil
	default:
		return nil, fmt.Errorf("unsupported tool: %s", name)
	}
}

func loadJSONFile(path string) (map[string]interface{}, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out map[string]interface{}
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func pickMapKeys(doc map[string]interface{}, key string) map[string]interface{} {
	value, _ := doc[key].(map[string]interface{})
	if value == nil {
		return map[string]interface{}{}
	}
	return value
}
