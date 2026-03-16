package service

import (
	"log"
	"strings"
	"sync"
	"time"
)

type AdapterInfo struct {
	ID       string    `json:"id"`
	Source   string    `json:"source"`
	LoadedAt time.Time `json:"loaded_at"`
}

type AdapterRouterService struct {
	ActiveAdapters map[string]*AdapterInfo
	RoutingTable   map[string]string // intent -> adapter_id
	IntentLabels   []string
	MaxAdapters    int
	Mu             sync.Mutex
	Orchestrator   *GoOrchestrator
}

func NewAdapterRouterService(orch *GoOrchestrator) *AdapterRouterService {
	return &AdapterRouterService{
		ActiveAdapters: make(map[string]*AdapterInfo),
		RoutingTable: map[string]string{
			"math":     "lora-math-v1",
			"coding":   "lora-coding-v2",
			"creative": "lora-creative-v1",
			"logic":    "lora-logic-v1",
		},
		IntentLabels: []string{"general", "math", "coding", "creative", "logic"},
		MaxAdapters:  3,
		Orchestrator: orch,
	}
}

func (s *AdapterRouterService) RouteInput(text string) (string, string, float64) {
	// 1. Get Embeddings (Use native memory bridge or python bridge)
	// For now, let's assume a simple keyword heuristic for intent if embeddings down
	intent := "general"
	if containsAny(text, []string{"calculate", "equation", "sum", "integral"}) {
		intent = "math"
	} else if containsAny(text, []string{"code", "python", "script", "function", "golang"}) {
		intent = "coding"
	} else if containsAny(text, []string{"story", "poem", "write", "creative"}) {
		intent = "creative"
	} else if containsAny(text, []string{"solve", "logic", "puzzle", "deduce"}) {
		intent = "logic"
	}

	adapterID := s.RoutingTable[intent]
	return intent, adapterID, 1.0
}

func (s *AdapterRouterService) ApplyRouting(adapterID string) (bool, error) {
	s.Mu.Lock()
	defer s.Mu.Unlock()

	// 1. Check if already active
	if _, ok := s.ActiveAdapters[adapterID]; ok {
		s.ActiveAdapters[adapterID].LoadedAt = time.Now() // Refresh LRU
		return true, nil
	}

	// 2. VRAM Safety: Unload oldest if full
	if len(s.ActiveAdapters) >= s.MaxAdapters {
		var oldestID string
		var oldestTime time.Time = time.Now().Add(1 * time.Hour)
		for id, info := range s.ActiveAdapters {
			if info.LoadedAt.Before(oldestTime) {
				oldestTime = info.LoadedAt
				oldestID = id
			}
		}
		if oldestID != "" {
			log.Printf("[Router] Unloading oldest adapter %s to free VRAM", oldestID)
			delete(s.ActiveAdapters, oldestID)
			// Tell Python to unload
			s.Orchestrator.Execute("unload_adapter", map[string]interface{}{"adapter_id": oldestID}, 10*time.Second)
		}
	}

	// 3. Load via Python Bridge
	log.Printf("[Router] Requesting Python load for adapter %s", adapterID)
	resp, err := s.Orchestrator.Execute("load_adapter", map[string]interface{}{"adapter_id": adapterID}, 60*time.Second)
	if err != nil {
		return false, err
	}

	success := false
	if m, ok := resp.(map[string]interface{}); ok {
		success, _ = m["success"].(bool)
	}

	if success {
		s.ActiveAdapters[adapterID] = &AdapterInfo{
			ID:       adapterID,
			Source:   "hf",
			LoadedAt: time.Now(),
		}
	}

	return success, nil
}

func containsAny(text string, keywords []string) bool {
	lower := strings.ToLower(text)
	for _, kw := range keywords {
		if strings.Contains(lower, kw) {
			return true
		}
	}
	return false
}
