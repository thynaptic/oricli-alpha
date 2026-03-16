package service

import (
	"log"
	"sync"
	"time"
)

type ModuleState string

const (
	StateOnline   ModuleState = "online"
	StateOffline  ModuleState = "offline"
	StateDegraded ModuleState = "degraded"
)

type HealthStatus struct {
	Name           string      `json:"name"`
	State          ModuleState `json:"state"`
	Latency        float64     `json:"latency_ms"`
	LastCheck      time.Time   `json:"last_check"`
	FailureCount   int         `json:"failure_count"`
	Error          string      `json:"error,omitempty"`
}

type MonitorService struct {
	Statuses map[string]*HealthStatus
	mu       sync.RWMutex
	Interval time.Duration
	StopCh   chan struct{}
}

func NewMonitorService() *MonitorService {
	return &MonitorService{
		Statuses: make(map[string]*HealthStatus),
		Interval: 10 * time.Second,
		StopCh:   make(chan struct{}),
	}
}

func (s *MonitorService) Start(checkFunc func()) {
	go func() {
		ticker := time.NewTicker(s.Interval)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				checkFunc()
			case <-s.StopCh:
				return
			}
		}
	}()
	log.Println("[Monitor] Health monitoring started.")
}

func (s *MonitorService) UpdateStatus(name string, state ModuleState, latency float64, err string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	status, ok := s.Statuses[name]
	if !ok {
		status = &HealthStatus{Name: name}
		s.Statuses[name] = status
	}

	status.State = state
	status.Latency = latency
	status.LastCheck = time.Now()
	status.Error = err

	if state == StateOffline || state == StateDegraded {
		status.FailureCount++
		if status.FailureCount > 3 {
			log.Printf("[Monitor] ALERT: Module %s is consistently failing!", name)
		}
	} else {
		status.FailureCount = 0
	}
}

func (s *MonitorService) GetModuleState(name string) ModuleState {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if status, ok := s.Statuses[name]; ok {
		return status.State
	}
	return StateOnline // Default to online if unknown
}

func (s *MonitorService) ListStatuses() []*HealthStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	list := make([]*HealthStatus, 0, len(s.Statuses))
	for _, v := range s.Statuses {
		list = append(list, v)
	}
	return list
}

func (s *MonitorService) Stop() {
	close(s.StopCh)
}
