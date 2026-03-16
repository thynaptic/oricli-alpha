package node

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
	pb "github.com/thynaptic/oricli-go/pkg/rpc"
	"github.com/thynaptic/oricli-go/pkg/service"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// GoHiveNode represents a Go-based sidecar for a Python Brain Module
type GoHiveNode struct {
	ID             string
	ModuleName     string
	Operations     []string
	Bus            *bus.SwarmBus
	GrpcConn       *grpc.ClientConn
	GrpcClient     pb.ModuleServiceClient
	ProfileService *service.AgentProfileService
	Monitor        *service.MonitorService
}

// NewGoHiveNode creates a new sidecar and connects it to the Python gRPC worker
func NewGoHiveNode(moduleName string, operations []string, grpcAddr string, swarmBus *bus.SwarmBus, profileService *service.AgentProfileService, monitor *service.MonitorService) (*GoHiveNode, error) {
	conn, err := grpc.NewClient(grpcAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to gRPC worker: %w", err)
	}

	client := pb.NewModuleServiceClient(conn)
	node := &GoHiveNode{
		ID:             fmt.Sprintf("go_sidecar_%s", moduleName),
		ModuleName:     moduleName,
		Operations:     operations,
		Bus:            swarmBus,
		GrpcConn:       conn,
		GrpcClient:     client,
		ProfileService: profileService,
		Monitor:        monitor,
	}

	return node, nil
}

// Start initiates the subscription to the bus
func (n *GoHiveNode) Start() {
	n.Bus.Subscribe("tasks.cfp", n.onCFP)
	n.Bus.Subscribe(fmt.Sprintf("tasks.accept.%s", n.ID), n.onAccept)
}

// onCFP handles Call for Proposals and publishes BIDs
func (n *GoHiveNode) onCFP(msg bus.Message) {
	// Check health first
	if n.Monitor != nil && n.Monitor.GetModuleState("python_worker") == service.StateOffline {
		return
	}

	operation, ok := msg.Payload["operation"].(string)
	if !ok {
		return
	}

	// Check if this module can handle the requested operation
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

	var activeProfile *service.AgentProfile
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

	if activeProfile != nil {
		bidPayload["skill_overlays"] = activeProfile.SkillOverlays
	}

	n.Bus.Publish(bus.Message{
		Protocol:    bus.BID,
		Topic:       fmt.Sprintf("tasks.bid.%s", taskID),
		SenderID:    n.ID,
		RecipientID: msg.SenderID,
		Payload:     bidPayload,
	})
}

// onAccept handles accepted bids and executes the task on the Python worker
func (n *GoHiveNode) onAccept(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	operation, _ := msg.Payload["operation"].(string)
	params, _ := msg.Payload["params"].(map[string]interface{})

	paramsJSON, _ := json.Marshal(params)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	log.Printf("[%s] Executing %s for task %s via gRPC", n.ID, operation, taskID)

	resp, err := n.GrpcClient.ExecuteOperation(ctx, &pb.ExecuteRequest{
		ModuleName: n.ModuleName,
		Operation:  operation,
		ParamsJson: string(paramsJSON),
		TaskId:     taskID,
	})

	if err != nil {
		n.Bus.Publish(bus.Message{
			Protocol:    bus.ERROR,
			Topic:       fmt.Sprintf("tasks.error.%s", taskID),
			SenderID:    n.ID,
			RecipientID: msg.SenderID,
			Payload:     map[string]interface{}{"error": err.Error(), "task_id": taskID},
		})
		return
	}

	if !resp.Success {
		n.Bus.Publish(bus.Message{
			Protocol:    bus.ERROR,
			Topic:       fmt.Sprintf("tasks.error.%s", taskID),
			SenderID:    n.ID,
			RecipientID: msg.SenderID,
			Payload:     map[string]interface{}{"error": resp.ErrorMessage, "task_id": taskID},
		})
		return
	}

	var result map[string]interface{}
	json.Unmarshal([]byte(resp.ResultJson), &result)

	n.Bus.Publish(bus.Message{
		Protocol:    bus.RESULT,
		Topic:       fmt.Sprintf("tasks.result.%s", taskID),
		SenderID:    n.ID,
		RecipientID: msg.SenderID,
		Payload:     map[string]interface{}{"result": result, "task_id": taskID},
	})
}

func (n *GoHiveNode) Stop() {
	n.GrpcConn.Close()
}
