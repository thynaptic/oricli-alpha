package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// CodeEngineModule provides code analysis and generation via the Swarm Bus
type CodeEngineModule struct {
	Bus     *bus.SwarmBus
	Service *service.CodeEngineService
	ID      string
}

// NewCodeEngineModule creates a new code engine module
func NewCodeEngineModule(swarmBus *bus.SwarmBus, svc *service.CodeEngineService) *CodeEngineModule {
	return &CodeEngineModule{
		Bus:     swarmBus,
		Service: svc,
		ID:      "code_engine",
	}
}

// Start initiates the subscription to the bus
func (n *CodeEngineModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *CodeEngineModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	supportedOps := map[string]bool{
		"generate_code":      true,
		"refine_code":        true,
		"optimize_code":      true,
		"translate_code":     true,
		"formally_verify":    true,
		"execute_in_sandbox": true,
	}

	if !supportedOps[operation] { return }

	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": 0.4,
			"confidence": 1.0,
		},
	})
}

func (n *CodeEngineModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	var result interface{}
	var err error

	switch operation {
	case "generate_code":
		result, err = n.Service.GenerateCodeReasoning(params)
	case "refine_code":
		result, err = n.Service.RefineCode(params)
	case "optimize_code":
		code, _ := params["code"].(string)
		lang, _ := params["language"].(string)
		text, e := n.Service.OptimizeCode(ctx, code, lang)
		result, err = map[string]interface{}{"optimized_code": text}, e
	case "translate_code":
		code, _ := params["code"].(string)
		src, _ := params["source_language"].(string)
		tgt, _ := params["target_language"].(string)
		text, e := n.Service.TranslateCode(ctx, code, src, tgt)
		result, err = map[string]interface{}{"translated_code": text}, e
	case "formally_verify":
		code, _ := params["code"].(string)
		result, err = n.Service.FormallyVerify(ctx, code)
	case "execute_in_sandbox":
		cmd, _ := params["command"].(string)
		argsRaw, _ := params["args"].([]interface{})
		args := make([]string, len(argsRaw))
		for i, a := range argsRaw { args[i] = fmt.Sprintf("%v", a) }
		output, e := n.Service.ExecuteInSandbox(ctx, cmd, args)
		result, err = map[string]interface{}{"output": output}, e
	}

	resPayload := map[string]interface{}{
		"task_id": taskID,
		"success": err == nil,
	}
	if err != nil {
		resPayload["error"] = err.Error()
	} else {
		resPayload["result"] = result
	}

	n.Bus.Publish(bus.Message{
		Topic:   "tasks.result",
		Payload: resPayload,
	})
}
