package service

import (
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

// --- ADAPTER INFERENCE ---

func (s *AdapterRouterService) ExecuteAdapterInference(params map[string]interface{}) (map[string]interface{}, error) {
	adapterID, _ := params["adapter_id"].(string)
	
	// Native Go logic to ensure adapter is loaded, then generate
	if _, ok := s.ActiveAdapters[adapterID]; !ok {
		s.ApplyRouting(adapterID)
	}
	
	// For now, proxy actual inference to Python which has the weights
	res, err := s.Orchestrator.Execute("lora_inference.generate", params, 60*time.Second)
	if err != nil { return nil, err }
	return res.(map[string]interface{}), nil
}

// --- EXISTING METHODS ---

func (s *AdapterRouterService) RouteInput(text string) (string, string, float64) {
	intent := "general"
	if containsAny(text, []string{"calculate", "equation", "sum", "integral"}) { intent = "math" }
	if containsAny(text, []string{"code", "python", "script", "function", "golang"}) { intent = "coding" }
	if containsAny(text, []string{"story", "poem", "write", "creative"}) { intent = "creative" }
	if containsAny(text, []string{"solve", "logic", "puzzle", "deduce"}) { intent = "logic" }
	return intent, s.RoutingTable[intent], 1.0
}

func (s *AdapterRouterService) ApplyRouting(adapterID string) (bool, error) {
	s.Mu.Lock()
	defer s.Mu.Unlock()
	if _, ok := s.ActiveAdapters[adapterID]; ok {
		s.ActiveAdapters[adapterID].LoadedAt = time.Now()
		return true, nil
	}
	if len(s.ActiveAdapters) >= s.MaxAdapters {
		var oldestID string
		oldestTime := time.Now().Add(1 * time.Hour)
		for id, info := range s.ActiveAdapters { if info.LoadedAt.Before(oldestTime) { oldestTime = info.LoadedAt; oldestID = id } }
		if oldestID != "" {
			delete(s.ActiveAdapters, oldestID)
			s.Orchestrator.Execute("unload_adapter", map[string]interface{}{"adapter_id": oldestID}, 10*time.Second)
		}
	}
	resp, err := s.Orchestrator.Execute("load_adapter", map[string]interface{}{"adapter_id": adapterID}, 60*time.Second)
	if err != nil { return false, err }
	success := false
	if m, ok := resp.(map[string]interface{}); ok { success, _ = m["success"].(bool) }
	if success { s.ActiveAdapters[adapterID] = &AdapterInfo{ID: adapterID, Source: "hf", LoadedAt: time.Now()} }
	return success, nil
}

func containsAny(text string, keywords []string) bool {
	lower := strings.ToLower(text)
	for _, kw := range keywords { if strings.Contains(lower, kw) { return true } }
	return false
}
