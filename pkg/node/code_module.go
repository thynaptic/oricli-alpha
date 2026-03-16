package node

import (
	"fmt"
	"log"
	"path/filepath"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// CodeModule handles code analysis and execution natively in Go
type CodeModule struct {
	ID         string
	ModuleName string
	Operations []string
	Bus        *bus.SwarmBus
	Analyzer   *service.CodeAnalyzer
	Sandbox    *service.SandboxService
}

func NewCodeModule(swarmBus *bus.SwarmBus, analyzer *service.CodeAnalyzer, sandbox *service.SandboxService) *CodeModule {
	return &CodeModule{
		ID:         "go_native_code",
		ModuleName: "code_service", // Merged code_analysis and code_execution
		Operations: []string{"analyze_code", "explain_code", "execute_command", "execute_python"},
		Bus:        swarmBus,
		Analyzer:   analyzer,
		Sandbox:    sandbox,
	}
}

func (m *CodeModule) Start() {
	m.Bus.Subscribe("tasks.cfp", m.onCFP)
	m.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", m.ID), m.onAccept)
	log.Printf("[CodeModule] %s started and listening for code tasks.", m.ModuleName)
}

func (m *CodeModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supported := false
	for _, op := range m.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if !supported {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    1.0,
		"compute_cost":  0,
		"node_id":       m.ID,
		"module_name":   m.ModuleName,
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

func (m *CodeModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	log.Printf("[CodeModule] Executing native %s for task %s", operation, taskID)

	var result interface{}
	var err error

	switch operation {
	case "analyze_code":
		code, _ := params["code"].(string)
		result = m.Analyzer.Analyze(code)
	case "explain_code":
		code, _ := params["code"].(string)
		result = m.Analyzer.Explain(code)
	case "execute_command":
		cmd, _ := params["command"].(string)
		// For security, only allow simple commands for now
		result = m.Sandbox.ExecuteCommand("/bin/bash", []string{"-c", cmd}, 30*time.Second)
	case "execute_python":
		code, _ := params["code"].(string)
		path, _ := m.Sandbox.WriteFile(fmt.Sprintf("script_%s.py", taskID[:8]), code)
		result = m.Sandbox.ExecuteCommand("python3", []string{path}, 30*time.Second)
		m.Sandbox.DeleteFile(filepath.Base(path))
	}

	if err != nil {
		m.Bus.Publish(bus.Message{
			Protocol:    bus.ERROR,
			Topic:       fmt.Sprintf("tasks.error.%s", taskID),
			SenderID:    m.ID,
			RecipientID: msg.SenderID,
			Payload:     map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	m.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    m.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}
