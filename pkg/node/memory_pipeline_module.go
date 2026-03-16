package node

import (
	"fmt"

	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// MemoryPipelineModule provides conversational and episodic memory processing via the Swarm Bus
type MemoryPipelineModule struct {
	Bus     *bus.SwarmBus
	Service *service.MemoryPipelineService
	ID      string
}

// NewMemoryPipelineModule creates a new memory pipeline module
func NewMemoryPipelineModule(swarmBus *bus.SwarmBus, svc *service.MemoryPipelineService) *MemoryPipelineModule {
	return &MemoryPipelineModule{
		Bus:     swarmBus,
		Service: svc,
		ID:      "memory_pipeline",
	}
}

// Start initiates the subscription to the bus
func (n *MemoryPipelineModule) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

func (n *MemoryPipelineModule) onCFP(msg bus.Message) {
	operation, ok := msg.Payload["operation"].(string)
	if !ok { return }

	supportedOps := map[string]bool{
		"remember_context":        true,
		"get_reference":           true,
		"build_on_previous":       true,
		"track_topic_continuity":  true,
		"natural_reference":       true,
		"process_memories":        true,
		"clean_and_deduplicate":   true,
		"cluster_memories":        true,
		"extract_patterns":        true,
		"detect_outliers":         true,
		"store_reaction":          true,
		"retrieve_reaction":       true,
		"process_long_term":       true,
		"analyze_dynamics":        true,
	}

	if !supportedOps[operation] { return }

	taskID, _ := msg.Payload["task_id"].(string)

	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    fmt.Sprintf("tasks.bid.%s", taskID),
		Payload: map[string]interface{}{
			"task_id":      taskID,
			"agent_id":     n.ID,
			"compute_cost": 0.15,
			"confidence":   1.0,
		},
	})
}

func (n *MemoryPipelineModule) onAccept(msg bus.Message) {
	taskID := msg.Payload["task_id"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})
	operation, _ := msg.Payload["operation"].(string)

	var result interface{}
	var err error

	switch operation {
	case "remember_context":
		result, err = n.Service.RememberContext(params)
	case "get_reference":
		result, err = n.Service.GetReference(params)
	case "build_on_previous":
		result, err = n.Service.BuildOnPrevious(params)
	case "track_topic_continuity":
		result, err = n.Service.TrackTopicContinuity(params)
	case "natural_reference":
		result, err = n.Service.NaturalReference(params)
	case "process_memories":
		result, err = n.Service.ProcessMemories(params)
	case "clean_and_deduplicate":
		result, err = n.Service.CleanAndDeduplicate(params)
	case "cluster_memories":
		result, err = n.Service.ClusterMemories(params)
	case "extract_patterns":
		result, err = n.Service.ExtractPatterns(params)
	case "detect_outliers":
		result, err = n.Service.DetectOutliers(params)
	case "store_reaction":
		result, err = n.Service.StoreReaction(params)
	case "retrieve_reaction":
		result, err = n.Service.RetrieveReaction(params)
	case "process_long_term":
		result, err = n.Service.ProcessLongTerm(params)
	case "analyze_dynamics":
		result, err = n.Service.AnalyzeDynamics(params)
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
