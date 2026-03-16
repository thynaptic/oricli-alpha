package service

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Insight struct {
	ID             string                 `json:"id"`
	Insight        string                 `json:"insight"`
	SourceA        string                 `json:"source_a"`
	SourceB        string                 `json:"source_b"`
	RelevanceScore float64                `json:"relevance_score"`
	DreamedAt      string                 `json:"dreamed_at"`
	Trained        bool                   `json:"trained"`
	Metadata       map[string]interface{} `json:"metadata"`
}

type InsightService struct {
	FilePath string
	mu       sync.Mutex
}

func NewInsightService(path string) *InsightService {
	if path == "" {
		path = "oricli_core/data/synthetic_insights.jsonl"
	}
	os.MkdirAll(filepath.Dir(path), 0755)
	return &InsightService{FilePath: path}
}

func (s *InsightService) RecordInsight(connection, sourceA, sourceB string, score float64, metadata map[string]interface{}) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("%d", time.Now().UnixNano()/1e6)
	entry := Insight{
		ID:             id,
		Insight:        connection,
		SourceA:        sourceA,
		SourceB:        sourceB,
		RelevanceScore: score,
		DreamedAt:      time.Now().Format(time.RFC3339),
		Trained:        false,
		Metadata:       metadata,
	}

	data, err := json.Marshal(entry)
	if err != nil {
		return "", err
	}

	f, err := os.OpenFile(s.FilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return "", err
	}
	defer f.Close()

	if _, err := f.Write(append(data, '\n')); err != nil {
		return "", err
	}

	return id, nil
}

func (s *InsightService) ListUntrainedInsights(minScore float64) ([]Insight, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	f, err := os.Open(s.FilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return []Insight{}, nil
		}
		return nil, err
	}
	defer f.Close()

	var insights []Insight
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		var in Insight
		if err := json.Unmarshal(scanner.Bytes(), &in); err != nil {
			continue
		}
		if !in.Trained && in.RelevanceScore >= minScore {
			insights = append(insights, in)
		}
	}

	return insights, nil
}

func (s *InsightService) MarkAsTrained(ids []string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	all, err := s.readAll()
	if err != nil {
		return err
	}

	idMap := make(map[string]bool)
	for _, id := range ids {
		idMap[id] = true
	}

	for i, in := range all {
		if idMap[in.ID] {
			all[i].Trained = true
		}
	}

	return s.writeAll(all)
}

func (s *InsightService) readAll() ([]Insight, error) {
	f, err := os.Open(s.FilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return []Insight{}, nil
		}
		return nil, err
	}
	defer f.Close()

	var insights []Insight
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		var in Insight
		if err := json.Unmarshal(scanner.Bytes(), &in); err != nil {
			continue
		}
		insights = append(insights, in)
	}
	return insights, nil
}

func (s *InsightService) writeAll(ins []Insight) error {
	f, err := os.Create(s.FilePath)
	if err != nil {
		return err
	}
	defer f.Close()

	for _, in := range ins {
		data, _ := json.Marshal(in)
		f.Write(append(data, '\n'))
	}
	return nil
}
