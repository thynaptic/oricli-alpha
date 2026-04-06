package service

func RegisterBrowserTools(toolSvc *ToolService) {
	if toolSvc == nil {
		return
	}

	toolSvc.RegisterTool(Tool{
		Name:        "browser_create_session",
		Description: "Create a new browser automation session.",
		ModuleName:  "",
		Operation:   "browser_create_session",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"headless":        map[string]interface{}{"type": "boolean"},
				"viewport_width":  map[string]interface{}{"type": "integer"},
				"viewport_height": map[string]interface{}{"type": "integer"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_open",
		Description: "Open a URL in an existing browser session.",
		ModuleName:  "",
		Operation:   "browser_open",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id", "url"},
			"properties": map[string]interface{}{
				"session_id": map[string]interface{}{"type": "string"},
				"url":        map[string]interface{}{"type": "string"},
				"wait_until": map[string]interface{}{"type": "string"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_snapshot",
		Description: "Capture the current DOM snapshot and interactive refs for a session.",
		ModuleName:  "",
		Operation:   "browser_snapshot",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id"},
			"properties": map[string]interface{}{
				"session_id": map[string]interface{}{"type": "string"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_action",
		Description: "Execute a browser interaction like click, fill, press, wait_for, or get_text using refs, selectors, labels, text, roles, or URL patterns.",
		ModuleName:  "",
		Operation:   "browser_action",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id", "action"},
			"properties": map[string]interface{}{
				"session_id":  map[string]interface{}{"type": "string"},
				"action":      map[string]interface{}{"type": "string"},
				"ref":         map[string]interface{}{"type": "string"},
				"selector":    map[string]interface{}{"type": "string"},
				"text":        map[string]interface{}{"type": "string"},
				"text_query":  map[string]interface{}{"type": "string"},
				"label":       map[string]interface{}{"type": "string"},
				"role":        map[string]interface{}{"type": "string"},
				"name":        map[string]interface{}{"type": "string"},
				"url_pattern": map[string]interface{}{"type": "string"},
				"key":         map[string]interface{}{"type": "string"},
				"timeout_ms":  map[string]interface{}{"type": "integer"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_screenshot",
		Description: "Capture a screenshot for the current session.",
		ModuleName:  "",
		Operation:   "browser_screenshot",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id"},
			"properties": map[string]interface{}{
				"session_id": map[string]interface{}{"type": "string"},
				"full_page":  map[string]interface{}{"type": "boolean"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_save_state",
		Description: "Persist the current browser storage state under a reusable name.",
		ModuleName:  "",
		Operation:   "browser_save_state",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id", "state_name"},
			"properties": map[string]interface{}{
				"session_id": map[string]interface{}{"type": "string"},
				"state_name": map[string]interface{}{"type": "string"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_load_state",
		Description: "Create a new browser session from a previously saved browser storage state.",
		ModuleName:  "",
		Operation:   "browser_load_state",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"state_name"},
			"properties": map[string]interface{}{
				"state_name":      map[string]interface{}{"type": "string"},
				"headless":        map[string]interface{}{"type": "boolean"},
				"viewport_width":  map[string]interface{}{"type": "integer"},
				"viewport_height": map[string]interface{}{"type": "integer"},
			},
		},
	})

	toolSvc.RegisterTool(Tool{
		Name:        "browser_close",
		Description: "Close an existing browser automation session.",
		ModuleName:  "",
		Operation:   "browser_close",
		Parameters: map[string]interface{}{
			"type":     "object",
			"required": []string{"session_id"},
			"properties": map[string]interface{}{
				"session_id": map[string]interface{}{"type": "string"},
			},
		},
	})
}
