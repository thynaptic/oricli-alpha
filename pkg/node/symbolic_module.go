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
	if !ok { return }

	if operation != "solve" && operation != "check_satisfiability" && operation != "solve_web_of_lies" {
		return
	}

	taskID, _ := msg.Payload["task_id"].(string)

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"agent_id":     n.ID,
			"compute_cost": 0.4,
			"confidence":   1.0,
		},
	})
}

func (n *SymbolicModule) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
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

	if err != nil {
		n.Bus.Publish(bus.Message{
			Protocol: bus.ERROR,
			Topic:    "tasks.error",
			Payload: map[string]interface{}{
				"task_id": taskID,
				"error":   err.Error(),
			},
		})
		return
	}

	// Publish result
	n.Bus.Publish(bus.Message{
		Protocol: bus.RESULT,
		Topic:    "tasks.result",
		Payload: map[string]interface{}{
			"task_id": taskID,
			"success": true,
			"result":  result,
		},
	})
}
