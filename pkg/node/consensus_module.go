package node

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ConsensusModule provides Swarm Consensus via the Swarm Bus
type ConsensusModule struct {
	Bus       *bus.SwarmBus
	Consensus *service.SwarmConsensusService
	ID        string
}

// NewConsensusModule creates a new consensus module
func NewConsensusModule(swarmBus *bus.SwarmBus, consensus *service.SwarmConsensusService) *ConsensusModule {
	return &ConsensusModule{
		Bus:       swarmBus,
		Consensus: consensus,
		ID:        "swarm_consensus",
	}
}

// Start initiates the subscription to the bus
func (n *ConsensusModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *ConsensusModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	if operation != "reach_consensus" && operation != "swarm_consensus" {
		return
	}

	// Bid for the task
	n.Bus.Publish(bus.Message{
		Topic: "tasks.bid",
		Payload: map[string]interface{}{
			"task_id":    msg.Payload["task_id"],
			"agent_id":   n.ID,
			"bid_amount": 0.1, // High efficiency, low cost
			"confidence": 1.0,
		},
	})
}

func (n *ConsensusModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	// Execute
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	opinionsRaw, _ := params["opinions"].([]interface{})
	opinions := make([]service.AgentOpinion, len(opinionsRaw))
	for i, o := range opinionsRaw {
		omap, _ := o.(map[string]interface{})
		opinions[i] = service.AgentOpinion{
			AgentID:    fmt.Sprintf("%v", omap["agent_id"]),
			Content:    fmt.Sprintf("%v", omap["content"]),
			Confidence: service.ToFloat64(omap["confidence"]),
		}
	}

	policyStr, _ := params["policy"].(string)
	policy := service.ConsensusPolicy(policyStr)
	if policy == "" {
		policy = service.PolicyMajority
	}

	result, err := n.Consensus.ReachConsensus(ctx, opinions, policy)

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
