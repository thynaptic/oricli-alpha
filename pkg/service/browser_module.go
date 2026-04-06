package service

import (
	"context"
	"fmt"
)

// BrowserAutomationModule exposes browser automation through the native module contract.
type BrowserAutomationModule struct {
	service *BrowserService
	name    string
}

func NewBrowserAutomationModule(svc *BrowserService) *BrowserAutomationModule {
	return &BrowserAutomationModule{
		service: svc,
		name:    "browser_automation_service",
	}
}

func (m *BrowserAutomationModule) Initialize(ctx context.Context) error {
	if m.service == nil {
		return fmt.Errorf("browser service is nil")
	}
	return nil
}

func (m *BrowserAutomationModule) Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error) {
	if m.service == nil {
		return nil, fmt.Errorf("browser service is nil")
	}

	switch operation {
	case "browser_health", "health_check":
		ok, sessions, err := m.service.Health(ctx)
		if err != nil {
			return map[string]interface{}{
				"ok":       false,
				"sessions": sessions,
				"error":    err.Error(),
			}, nil
		}
		return map[string]interface{}{
			"ok":       ok,
			"sessions": sessions,
		}, nil

	case "browser_create_session":
		req := BrowserCreateSessionRequest{
			Headless: boolParam(params, "headless", true),
		}
		req.Viewport.Width = intParam(params, "viewport_width", 1440)
		req.Viewport.Height = intParam(params, "viewport_height", 900)
		return m.service.CreateSession(ctx, req)

	case "browser_open":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		rawURL, err := requiredString(params, "url")
		if err != nil {
			return nil, err
		}
		return m.service.Open(ctx, sessionID, BrowserOpenRequest{
			URL:       rawURL,
			WaitUntil: stringParam(params, "wait_until", "networkidle"),
		})

	case "browser_snapshot":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		return m.service.Snapshot(ctx, sessionID)

	case "browser_action":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		return m.service.Action(ctx, sessionID, BrowserActionRequest{
			Action:     stringParam(params, "action", ""),
			Ref:        stringParam(params, "ref", ""),
			Selector:   stringParam(params, "selector", ""),
			Text:       stringParam(params, "text", ""),
			TextQuery:  stringParam(params, "text_query", ""),
			Label:      stringParam(params, "label", ""),
			Role:       stringParam(params, "role", ""),
			Name:       stringParam(params, "name", ""),
			URLPattern: stringParam(params, "url_pattern", ""),
			Key:        stringParam(params, "key", ""),
			TimeoutMs:  intParam(params, "timeout_ms", 10000),
		})

	case "browser_screenshot":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		return m.service.Screenshot(ctx, sessionID, boolParam(params, "full_page", false))

	case "browser_save_state":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		stateName, err := requiredString(params, "state_name")
		if err != nil {
			return nil, err
		}
		return m.service.SaveState(ctx, sessionID, stateName)

	case "browser_load_state":
		stateName, err := requiredString(params, "state_name")
		if err != nil {
			return nil, err
		}
		req := BrowserLoadStateRequest{
			StateName: stateName,
			Headless:  boolParam(params, "headless", true),
		}
		req.Viewport.Width = intParam(params, "viewport_width", 1440)
		req.Viewport.Height = intParam(params, "viewport_height", 900)
		return m.service.LoadState(ctx, req)

	case "browser_close":
		sessionID, err := requiredString(params, "session_id")
		if err != nil {
			return nil, err
		}
		if err := m.service.CloseSession(ctx, sessionID); err != nil {
			return nil, err
		}
		return map[string]interface{}{"ok": true}, nil
	}

	return nil, fmt.Errorf("unknown browser operation: %s", operation)
}

func (m *BrowserAutomationModule) Metadata() ModuleMetadata {
	return ModuleMetadata{
		Name:        m.name,
		Version:     "0.1.0",
		Description: "Sovereign browser automation runtime backed by browserd",
		Author:      "Oricli-Alpha Core",
		IsGoNative:  true,
		Operations: []string{
			"health_check",
			"browser_health",
			"browser_create_session",
			"browser_open",
			"browser_snapshot",
			"browser_action",
			"browser_screenshot",
			"browser_save_state",
			"browser_load_state",
			"browser_close",
		},
	}
}

func (m *BrowserAutomationModule) Cleanup(ctx context.Context) error {
	return nil
}

func requiredString(params map[string]interface{}, key string) (string, error) {
	value := stringParam(params, key, "")
	if value == "" {
		return "", fmt.Errorf("missing %q parameter", key)
	}
	return value, nil
}

func stringParam(params map[string]interface{}, key, fallback string) string {
	if raw, ok := params[key].(string); ok {
		return raw
	}
	return fallback
}

func intParam(params map[string]interface{}, key string, fallback int) int {
	switch v := params[key].(type) {
	case int:
		return v
	case int32:
		return int(v)
	case int64:
		return int(v)
	case float64:
		return int(v)
	default:
		return fallback
	}
}

func boolParam(params map[string]interface{}, key string, fallback bool) bool {
	if raw, ok := params[key].(bool); ok {
		return raw
	}
	return fallback
}
