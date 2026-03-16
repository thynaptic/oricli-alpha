package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ReasoningStrategiesModule provides specialized reasoning patterns via the Swarm Bus
type ReasoningStrategiesModule struct {
	Bus        *bus.SwarmBus
	Strategies *service.ReasoningStrategyService
	ID         string
}

// NewReasoningStrategiesModule creates a new reasoning strategies module
func NewReasoningStrategiesModule(swarmBus *bus.SwarmBus, strategies *service.ReasoningStrategyService) *ReasoningStrategiesModule {
	return &ReasoningStrategiesModule{
		Bus:        swarmBus,
		Strategies: strategies,
		ID:         "go_reasoning_strategies",
	}
}

// Start initiates the subscription to the bus
func (n *ReasoningStrategiesModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *ReasoningStrategiesModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	supportedOps := map[string]bool{
		"analogical_reasoning":  true,
		"logical_deduction":     true,
		"decomposition":         true,
		"critical_thinking":     true,
		"hypothesis_generation": true,
		"causal_inference":      true,
		"counterfactual":        true,
		"step_by_step":          true,
		"verify":                true,
		"reflect":               true,
		"reason":                true,
	}

	if !supportedOps[operation] {
		return
	}

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": 0.3,
			"confidence": 0.8,
		},
	})
}

func (n *ReasoningStrategiesModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	query := fmt.Sprintf("%v", params["query"])
	contextStr := fmt.Sprintf("%v", params["context"])

	var result *service.StrategyResult
	var err error

	switch operation {
	case "analogical_reasoning":
		result, err = n.Strategies.AnalogicalReasoning(ctx, query, contextStr)
	case "logical_deduction":
		result, err = n.Strategies.LogicalDeduction(ctx, query, contextStr)
	case "decomposition":
		result, err = n.Strategies.Decomposition(ctx, query, contextStr)
	case "critical_thinking":
		result, err = n.Strategies.CriticalThinking(ctx, query, contextStr)
	case "hypothesis_generation":
		result, err = n.Strategies.HypothesisGeneration(ctx, query, contextStr)
	case "causal_inference":
		result, err = n.Strategies.CausalInference(ctx, query, contextStr)
	case "counterfactual":
		result, err = n.Strategies.CounterfactualAnalysis(ctx, query, contextStr)
	case "step_by_step":
		result, err = n.Strategies.StepByStepReasoning(ctx, query, contextStr)
	case "verify":
		result, err = n.Strategies.VerifyConclusion(ctx, query, contextStr)
	case "reflect":
		result, err = n.Strategies.ReflectOnReasoning(ctx, query)
	case "reason":
		rtype, _ := params["reasoning_type"].(string)
		switch rtype {
		case "analogical":
			result, err = n.Strategies.AnalogicalReasoning(ctx, query, contextStr)
		case "deduction":
			result, err = n.Strategies.LogicalDeduction(ctx, query, contextStr)
		case "decomposition":
			result, err = n.Strategies.Decomposition(ctx, query, contextStr)
		case "critical":
			result, err = n.Strategies.CriticalThinking(ctx, query, contextStr)
		case "hypothesis":
			result, err = n.Strategies.HypothesisGeneration(ctx, query, contextStr)
		case "causal":
			result, err = n.Strategies.CausalInference(ctx, query, contextStr)
		case "counterfactual":
			result, err = n.Strategies.CounterfactualAnalysis(ctx, query, contextStr)
		case "stepwise":
			result, err = n.Strategies.StepByStepReasoning(ctx, query, contextStr)
		default:
			result, err = n.Strategies.Decomposition(ctx, query, contextStr)
		}
	}

	// Publish result
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
