package service

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Lesson struct {
	Prompt    string                 `json:"prompt"`
	Response  string                 `json:"response"`
	Timestamp float64                `json:"timestamp"`
	Metadata  map[string]interface{} `json:"metadata"`
}

type AbsorptionService struct {
	FilePath string
	mu       sync.Mutex
}

func NewAbsorptionService(path string) *AbsorptionService {
	if path == "" {
		path = "oricli_core/data/jit_absorption.jsonl"
	}
	os.MkdirAll(filepath.Dir(path), 0755)
	return &AbsorptionService{FilePath: path}
}

func (s *AbsorptionService) RecordLesson(prompt, response string, metadata map[string]interface{}) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	entry := Lesson{
		Prompt:    prompt,
		Response:  response,
		Timestamp: float64(time.Now().Unix()),
		Metadata:  metadata,
	}

	data, err := json.Marshal(entry)
	if err != nil {
		return false
	}

	f, err := os.OpenFile(s.FilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return false
	}
	defer f.Close()

	if _, err := f.Write(append(data, '\n')); err != nil {
		return false
	}

	return true
}

func (s *AbsorptionService) GetBufferCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()

	f, err := os.Open(s.FilePath)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		count++
	}
	return count
}

func (s *AbsorptionService) ClearBuffer() {
	s.mu.Lock()
	defer s.mu.Unlock()

	os.Remove(s.FilePath)
	f, _ := os.Create(s.FilePath)
	f.Close()
}
