package service

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/bus"
)

// Orchestrator State
type OrchestratorStatus string

const (
	StatusIdle     OrchestratorStatus = "idle"
	StatusStarting OrchestratorStatus = "starting"
	StatusActive   OrchestratorStatus = "active"
	StatusError    OrchestratorStatus = "error"
)

// GoOrchestrator manages the Hive's coordination and lifecycle
type GoOrchestrator struct {
	Bus        *bus.SwarmBus
	Tasks      map[string]*TaskContext
	BrokerID   string
	Status     OrchestratorStatus
	mu         sync.RWMutex
	LoadOrder  []string
	Modules    map[string]bool // Known module names
	Classifier *DegradedModeClassifier
}

// Bid represents a proposal from a node
type Bid struct {
	NodeID      string
	Confidence  float64
	ComputeCost float64
	Timestamp   int64
}

// TaskContext tracks the lifecycle of a task being bid on
type TaskContext struct {
	TaskID    string
	Operation string
	Params    map[string]interface{}
	Bids      []Bid
	Deadline  time.Time
	ResultCh  chan interface{}
	mu        sync.Mutex
}

func NewGoOrchestrator(swarmBus *bus.SwarmBus, registry *ModuleRegistry) *GoOrchestrator {
	orch := &GoOrchestrator{
		Bus:        swarmBus,
		Tasks:      make(map[string]*TaskContext),
		BrokerID:   "go_broker_main",
		Status:     StatusIdle,
		Modules:    make(map[string]bool),
		Classifier: NewDegradedModeClassifier(registry),
	}
	// Global listener for bids and results
	swarmBus.Subscribe("*", orch.onMessage)
	return orch
}

func (o *GoOrchestrator) onMessage(msg bus.Message) {
	switch msg.Protocol {
	case bus.BID:
		o.handleBid(msg)
	case bus.RESULT:
		o.handleResult(msg)
	case bus.ERROR:
		o.handleError(msg)
	}
}

// Execute triggers a Call for Proposals and waits for the best bid to finish
func (o *GoOrchestrator) Execute(operation string, params map[string]interface{}, timeout time.Duration) (interface{}, error) {
	// Map operation if needed
	if o.Classifier != nil {
		if mapped, ok := o.Classifier.operationMappings[operation]; ok {
			log.Printf("[Orchestrator] Mapping legacy operation '%s' -> '%s'", operation, mapped)
			operation = mapped
		}
	}

	taskID := uuid.New().String()
	ctx := &TaskContext{
		TaskID:    taskID,
		Operation: operation,
		Params:    params,
		Deadline:  time.Now().Add(5 * time.Second), // Bidding window
		ResultCh:  make(chan interface{}, 1),
	}

	o.mu.Lock()
	o.Tasks[taskID] = ctx
	o.mu.Unlock()

	// 1. Broadcast CFP
	log.Printf("[Orchestrator] Task %s: Broadcasting CFP for %s", taskID, operation)
	o.Bus.Publish(bus.Message{
		Protocol: bus.CFP,
		Topic:    "tasks.cfp",
		SenderID: o.BrokerID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"operation": operation,
			"params":    params,
		},
	})

	// 2. Wait for Bidding Window
	time.Sleep(5 * time.Second)

	// 3. Selection
	ctx.mu.Lock()
	if len(ctx.Bids) == 0 {
		ctx.mu.Unlock()
		return nil, fmt.Errorf("no bids received for operation: %s", operation)
	}

	var bestBid Bid
	for _, b := range ctx.Bids {
		if b.Confidence > bestBid.Confidence {
			bestBid = b
		}
	}
	ctx.mu.Unlock()

	log.Printf("[Orchestrator] Task %s: WINNER IS %s (Conf: %.2f, Cost: %.2f)", taskID, bestBid.NodeID, bestBid.Confidence, bestBid.ComputeCost)

	// 4. Accept Bid
	o.Bus.Publish(bus.Message{
		Protocol:    bus.ACCEPT,
		Topic:       fmt.Sprintf("tasks.accept.%s", bestBid.NodeID),
		SenderID:    o.BrokerID,
		RecipientID: bestBid.NodeID,
		Payload: map[string]interface{}{
			"task_id":   taskID,
			"operation": operation,
			"params":    params,
		},
	})

	// 5. Wait for Result
	select {
	case result := <-ctx.ResultCh:
		return result, nil
	case <-time.After(timeout):
		return nil, fmt.Errorf("task %s timed out after %v", taskID, timeout)
	}
}

func (o *GoOrchestrator) handleBid(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	o.mu.RLock()
	ctx, ok := o.Tasks[taskID]
	o.mu.RUnlock()

	if !ok {
		return
	}

	bid := Bid{
		NodeID:    msg.SenderID,
		Timestamp: time.Now().UnixNano(),
	}

	// Safe conversion for confidence
	if conf, ok := msg.Payload["confidence"].(float64); ok {
		bid.Confidence = conf
	} else if conf, ok := msg.Payload["confidence"].(int); ok {
		bid.Confidence = float64(conf)
	}

	// Safe conversion for compute_cost
	if cost, ok := msg.Payload["compute_cost"].(float64); ok {
		bid.ComputeCost = cost
	} else if cost, ok := msg.Payload["compute_cost"].(int); ok {
		bid.ComputeCost = float64(cost)
	}

	ctx.mu.Lock()
	ctx.Bids = append(ctx.Bids, bid)
	ctx.mu.Unlock()
}

func (o *GoOrchestrator) handleResult(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	o.mu.RLock()
	ctx, ok := o.Tasks[taskID]
	o.mu.RUnlock()

	if !ok {
		return
	}

	ctx.ResultCh <- msg.Payload["result"]
}

func (o *GoOrchestrator) handleError(msg bus.Message) {
	taskID, _ := msg.Payload["task_id"].(string)
	o.mu.RLock()
	ctx, ok := o.Tasks[taskID]
	o.mu.RUnlock()

	if !ok {
		return
	}

	log.Printf("[Orchestrator] Task %s received error: %v", taskID, msg.Payload["error"])
	// Pass error to result channel to avoid hanging
	ctx.ResultCh <- fmt.Errorf("node error: %v", msg.Payload["error"])
}
