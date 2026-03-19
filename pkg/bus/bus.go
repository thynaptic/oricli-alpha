package bus

import (
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
)

// Protocol defines the swarm message types
type Protocol string

const (
	CFP    Protocol = "cfp"
	BID    Protocol = "bid"
	ACCEPT Protocol = "accept"
	REJECT Protocol = "reject"
	RESULT Protocol = "result"
	ERROR  Protocol = "error"
)

// Message represents a single message on the Swarm Bus
type Message struct {
	ID          string                 `json:"id"`
	Protocol    Protocol               `json:"protocol"`
	Topic       string                 `json:"topic"`
	SenderID    string                 `json:"sender_id"`
	RecipientID string                 `json:"recipient_id,omitempty"`
	Payload     map[string]interface{} `json:"payload"`
	Timestamp   int64                  `json:"timestamp"`
}

// Subscriber is a function that processes a message
type Subscriber func(msg Message)

// SwarmBus handles high-throughput message routing via Go Channels
type SwarmBus struct {
	subscribers  map[string][]Subscriber
	mu           sync.RWMutex
	messageCh    chan Message
	priorityCh   chan Message
	stopCh       chan struct{}
	msgPool      *sync.Pool
	Blackboard   map[string]interface{}
	BbMu         sync.RWMutex
	AvgLatencyMS float64 // Real-time transit latency
	msgCount     int64
	latencyMu    sync.RWMutex
}

// NewSwarmBus initializes the bus with pooled messages and priority routing
func NewSwarmBus(bufferSize int) *SwarmBus {
	bus := &SwarmBus{
		subscribers: make(map[string][]Subscriber),
		messageCh:   make(chan Message, bufferSize),
		priorityCh:  make(chan Message, bufferSize/10),
		stopCh:      make(chan struct{}),
		Blackboard:  make(map[string]interface{}),
		msgPool: &sync.Pool{
			New: func() interface{} {
				return &Message{}
			},
		},
	}
	go bus.startDispatcher()
	return bus
}

// GetMessage retrieves a message from the pool (Zero-Copy entry)
func (b *SwarmBus) GetMessage() *Message {
	return b.msgPool.Get().(*Message)
}

// PutMessage returns a message to the pool
func (b *SwarmBus) PutMessage(msg *Message) {
	msg.ID = ""
	msg.Payload = nil
	b.msgPool.Put(msg)
}

// Subscribe adds a handler for a specific topic
func (b *SwarmBus) Subscribe(topic string, sub Subscriber) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.subscribers[topic] = append(b.subscribers[topic], sub)
}

// SetState updates the global blackboard
func (b *SwarmBus) SetState(key string, val interface{}) {
	b.BbMu.Lock()
	defer b.BbMu.Unlock()
	b.Blackboard[key] = val
}

// GetState reads from the global blackboard
func (b *SwarmBus) GetState(key string) interface{} {
	b.BbMu.RLock()
	defer b.BbMu.RUnlock()
	return b.Blackboard[key]
}

func (b *SwarmBus) GetLatency() float64 {
	b.latencyMu.RLock()
	defer b.latencyMu.RUnlock()
	return b.AvgLatencyMS
}

// Publish drops a message onto the bus channel
func (b *SwarmBus) Publish(msg Message) {
	if msg.ID == "" {
		msg.ID = uuid.New().String()
	}
	if msg.Timestamp == 0 {
		msg.Timestamp = time.Now().UnixNano()
	}
	
	// Route to priority channel if it's a critical protocol
	targetCh := b.messageCh
	if msg.Protocol == ACCEPT || msg.Protocol == ERROR {
		targetCh = b.priorityCh
	}

	select {
	case targetCh <- msg:
		// Message queued
	default:
		fmt.Printf("[SwarmBus] Warning: Bus buffer full, dropping message %s\n", msg.ID)
	}
}

// startDispatcher runs in a goroutine and routes messages to subscribers
func (b *SwarmBus) startDispatcher() {
	for {
		select {
		case msg := <-b.priorityCh:
			b.dispatch(msg)
		case msg := <-b.messageCh:
			// Always check priority again to prevent starvation
			select {
			case pMsg := <-b.priorityCh:
				b.dispatch(pMsg)
				// Re-queue the original message
				b.messageCh <- msg
			default:
				b.dispatch(msg)
			}
		case <-b.stopCh:
			return
		}
	}
}

func (b *SwarmBus) dispatch(msg Message) {
	// Calculate transit latency
	transitTime := float64(time.Now().UnixNano()-msg.Timestamp) / 1e6 // ms
	b.latencyMu.Lock()
	b.msgCount++
	// Simple moving average for latency
	if b.AvgLatencyMS == 0 {
		b.AvgLatencyMS = transitTime
	} else {
		b.AvgLatencyMS = (b.AvgLatencyMS * 0.9) + (transitTime * 0.1)
	}
	b.latencyMu.Unlock()

	b.mu.RLock()
	subs, ok := b.subscribers[msg.Topic]
	wildcardSubs := b.subscribers["*"]
	b.mu.RUnlock()

	// Direct topic match
	if ok {
		for _, sub := range subs {
			go sub(msg) // Run each subscriber in its own goroutine for true parallelism
		}
	}

	// Global wildcard match
	for _, sub := range wildcardSubs {
		go sub(msg)
	}
}

func (b *SwarmBus) Stop() {
	close(b.stopCh)
}
