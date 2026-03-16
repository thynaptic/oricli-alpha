package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ARCSwarmModule provides ARC solving capabilities via the Swarm Bus
type ARCSwarmModule struct {
	Bus    *bus.SwarmBus
	Solver *service.ARCSolverService
	ID     string
}

// NewARCSwarmModule creates a new ARC swarm module
func NewARCSwarmModule(swarmBus *bus.SwarmBus, solver *service.ARCSolverService) *ARCSwarmModule {
	return &ARCSwarmModule{
		Bus:    swarmBus,
		Solver: solver,
		ID:     "arc_solver",
	}
}

// Start initiates the subscription to the bus
func (n *ARCSwarmModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *ARCSwarmModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	if operation != "solve_arc" && operation != "predict_arc" {
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
			"compute_cost": 0.5,
			"confidence":   0.9,
		},
	})
}

func (n *ARCSwarmModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second)
	defer cancel()

	// Parse task
	taskMap, _ := params["task"].(map[string]interface{})
	task := n.parseARCTask(taskMap)

	result, err := n.Solver.SolveTask(ctx, task)

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

func (n *ARCSwarmModule) parseARCTask(m map[string]interface{}) service.ARCTask {
	task := service.ARCTask{}
	
	trainInputs, _ := m["train_inputs"].([]interface{})
	task.TrainInputs = make([][][]int, len(trainInputs))
	for i, grid := range trainInputs {
		task.TrainInputs[i] = n.castGrid(grid.([]interface{}))
	}

	trainOutputs, _ := m["train_outputs"].([]interface{})
	task.TrainOutputs = make([][][]int, len(trainOutputs))
	for i, grid := range trainOutputs {
		task.TrainOutputs[i] = n.castGrid(grid.([]interface{}))
	}

	testInput, _ := m["test_input"].([]interface{})
	task.TestInput = n.castGrid(testInput)
	
	return task
}

func (n *ARCSwarmModule) castGrid(raw []interface{}) [][]int {
	grid := make([][]int, len(raw))
	for i, r := range raw {
		rowRaw, _ := r.([]interface{})
		grid[i] = make([]int, len(rowRaw))
		for j, v := range rowRaw {
			grid[i][j] = int(service.ToFloat64(v))
		}
	}
	return grid
}
