package kernel

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/bus"
)

// --- Pillar 54: Sovereign Scheduler (Temporal Cron) ---
// Manages autonomous task scheduling and re-injection into the Swarm Bus.

type ScheduledTask struct {
	ID        string                 `json:"id"`
	Operation string                 `json:"operation"`
	Params    map[string]interface{} `json:"params"`
	Interval  time.Duration          `json:"interval,omitempty"`
	timer     *time.Timer
	ticker    *time.Ticker
	quit      chan struct{}
}

type Scheduler struct {
	Bus    *bus.SwarmBus
	tasks  map[string]*ScheduledTask
	mu     sync.RWMutex
}

func NewScheduler(swarmBus *bus.SwarmBus) *Scheduler {
	return &Scheduler{
		Bus:   swarmBus,
		tasks: make(map[string]*ScheduledTask),
	}
}

// ScheduleTask creates a one-shot or recurring task.
func (s *Scheduler) ScheduleTask(operation string, params map[string]interface{}, delay time.Duration, interval time.Duration) string {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := uuid.New().String()[:8]
	task := &ScheduledTask{
		ID:        id,
		Operation: operation,
		Params:    params,
		Interval:  interval,
		quit:      make(chan struct{}),
	}

	if interval > 0 {
		// Recurring task
		task.ticker = time.NewTicker(interval)
		go func() {
			// Initial delay if specified
			if delay > 0 {
				time.Sleep(delay)
				s.trigger(task)
			}
			for {
				select {
				case <-task.ticker.C:
					s.trigger(task)
				case <-task.quit:
					return
				}
			}
		}()
	} else {
		// One-shot task
		task.timer = time.AfterFunc(delay, func() {
			s.trigger(task)
			s.mu.Lock()
			delete(s.tasks, id)
			s.mu.Unlock()
		})
	}

	s.tasks[id] = task
	log.Printf("[Scheduler] Task %s scheduled: %s (Delay: %v, Interval: %v)", id, operation, delay, interval)
	return id
}

func (s *Scheduler) CancelTask(id string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	task, ok := s.tasks[id]
	if !ok {
		return false
	}

	if task.timer != nil {
		task.timer.Stop()
	}
	if task.ticker != nil {
		task.ticker.Stop()
		close(task.quit)
	}

	delete(s.tasks, id)
	log.Printf("[Scheduler] Task %s cancelled.", id)
	return true
}

func (s *Scheduler) trigger(t *ScheduledTask) {
	log.Printf("[Scheduler] Triggering task %s: %s", t.ID, t.Operation)
	
	// Re-inject into Swarm Bus as a CFP (Call for Proposals)
	s.Bus.Publish(bus.Message{
		Protocol: bus.CFP,
		Topic:    "tasks.cfp",
		SenderID: "sovereign_scheduler",
		Payload: map[string]interface{}{
			"task_id":   fmt.Sprintf("cron-%s-%s", t.ID, uuid.New().String()[:4]),
			"operation":  t.Operation,
			"params":     t.Params,
			"scheduled": true,
		},
	})
}
