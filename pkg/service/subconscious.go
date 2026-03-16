package service

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type Vibration struct {
	Vector    []float32 `json:"vector"`
	Weight    float64   `json:"weight"`
	Timestamp int64     `json:"timestamp"`
	Source    string    `json:"source"`
}

type SubconsciousState struct {
	Buffer      []Vibration `json:"buffer"`
	MentalState []float32   `json:"mental_state"`
	LastUpdate  int64       `json:"last_update"`
}

type SubconsciousService struct {
	Buffer      []Vibration
	MentalState []float32
	BufferSize  int
	StatePath   string
	mu          sync.RWMutex
}

func NewSubconsciousService(path string) *SubconsciousService {
	if path == "" {
		path = "oricli_core/data/subconscious_state.json"
	}
	s := &SubconsciousService{
		BufferSize: 100,
		StatePath:  path,
	}
	s.Load()
	return s
}

func (s *SubconsciousService) Vibrate(vector []float32, weight float64, source string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	v := Vibration{
		Vector:    vector,
		Weight:    weight,
		Timestamp: time.Now().Unix(),
		Source:    source,
	}

	s.Buffer = append(s.Buffer, v)
	if len(s.Buffer) > s.BufferSize {
		s.Buffer = s.Buffer[1:]
	}

	s.recalculate()
	s.Save()
}

func (s *SubconsciousService) recalculate() {
	if len(s.Buffer) == 0 {
		s.MentalState = nil
		return
	}

	dim := len(s.Buffer[0].Vector)
	avg := make([]float32, dim)
	totalWeight := 0.0

	for _, v := range s.Buffer {
		totalWeight += v.Weight
	}

	if totalWeight < 1e-9 {
		// Fallback to simple average
		totalWeight = float64(len(s.Buffer))
		for _, v := range s.Buffer {
			for i := 0; i < dim; i++ {
				avg[i] += v.Vector[i] * (1.0 / float32(totalWeight))
			}
		}
	} else {
		for _, v := range s.Buffer {
			w := float32(v.Weight / totalWeight)
			for i := 0; i < dim; i++ {
				avg[i] += v.Vector[i] * w
			}
		}
	}

	s.MentalState = avg
}

func (s *SubconsciousService) GetMentalState() ([]float32, int) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.MentalState, len(s.Buffer)
}

func (s *SubconsciousService) Load() error {
	data, err := os.ReadFile(s.StatePath)
	if err != nil {
		return err
	}

	var state SubconsciousState
	if err := json.Unmarshal(data, &state); err != nil {
		return err
	}

	s.Buffer = state.Buffer
	s.MentalState = state.MentalState
	return nil
}

func (s *SubconsciousService) Save() error {
	state := SubconsciousState{
		Buffer:      s.Buffer,
		MentalState: s.MentalState,
		LastUpdate:  time.Now().Unix(),
	}

	data, err := json.Marshal(state)
	if err != nil {
		return err
	}

	return os.WriteFile(s.StatePath, data, 0644)
}
