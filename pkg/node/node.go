package node

import (
	"log"
	"sync"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// Module represents a sovereign unit of intelligence in the Hive
type Module struct {
	ID             string
	ModuleName     string
	Operations     []string
	Bus            *bus.SwarmBus
	ProfileService *service.AgentProfileService
	mu             sync.Mutex
	status         string
}

func NewModule(name string, ops []string, b *bus.SwarmBus, ps *service.AgentProfileService) *Module {
	return &Module{
		ID:             uuid.New().String()[:8],
		ModuleName:     name,
		Operations:     ops,
		Bus:            b,
		ProfileService: ps,
		status:         "idle",
	}
}

func (n *Module) Start() {
	log.Printf("[Module:%s] Hive Node %s online.", n.ModuleName, n.ID)
	// Listen for CFPs (Call for Proposals)
	n.Bus.Subscribe("tasks.cfp", n.handleCFP)
}

func (n *Module) handleCFP(msg bus.Message) {
	operation, _ := msg.Payload["operation"].(string)
	
	// Quick match check
	supported := false
	for _, op := range n.Operations {
		if op == operation {
			supported = true
			break
		}
	}

	if !supported {
		return
	}

	// Profile-aware constraint checking
	profileName, _ := msg.Payload["profile_name"].(string)
	taskType, _ := msg.Payload["task_type"].(string)
	agentType, _ := msg.Payload["agent_type"].(string)

	var activeProfile *model.AgentProfile
	if profileName != "" || taskType != "" || agentType != "" {
		if p, ok := n.ProfileService.ResolveProfile(profileName, taskType, agentType); ok {
			activeProfile = &p
			// Enforce allowed/blocked modules and operations
			if allowed, reason := n.ProfileService.IsAllowed(activeProfile, n.ModuleName, operation); !allowed {
				log.Printf("[%s] Bidding rejected by profile: %s", n.ID, reason)
				return
			}
		}
	}

	taskID, _ := msg.Payload["task_id"].(string)

	// Simple bidding logic: can be enhanced later with metrics and profile awareness
	bidPayload := map[string]interface{}{
		"task_id":      taskID,
		"operation":     operation,
		"confidence":    0.98, // Go sidecars are confident
		"compute_cost":  5,    // Go sidecar overhead is minimal
		"node_id":       n.ID,
		"module_name":   n.ModuleName,
	}

	n.Bus.Publish(bus.Message{
		Protocol: bus.BID,
		Topic:    "tasks.bid",
		SenderID: n.ID,
		Payload:  bidPayload,
	})
}

func (n *Module) SetStatus(s string) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.status = s
}
