package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// SymbolicModule provides Symbolic Solver access via the Swarm Bus
type SymbolicModule struct {
	Bus     *bus.SwarmBus
	Manager *service.SymbolicSolverManager
	ID      string
}

// NewSymbolicModule creates a new symbolic module
func NewSymbolicModule(swarmBus *bus.SwarmBus, manager *service.SymbolicSolverManager) *SymbolicModule {
	return &SymbolicModule{
		Bus:     swarmBus,
		Manager: manager,
		ID:      "symbolic_solver",
	}
}

// Start initiates the subscription to the bus
func (n *SymbolicModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *SymbolicModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "solve" && operation != "check_satisfiability" && operation != "solve_web_of_lies" {
		return
	}

	// Bid for the task
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

func (n *SymbolicModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	var result interface{}
	var err error

	if operation == "solve_web_of_lies" {
		text, _ := params["text"].(string)
		if text == "" { text, _ = params["query"].(string) }
		result, err = n.Manager.SolveWebOfLies(ctx, text)
	} else {
		result, err = n.Manager.Solve(ctx, params)
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
