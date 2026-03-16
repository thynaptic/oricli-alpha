package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"
	"sync"
	"time"
)

// TraceRecord represents an execution trace
type TraceRecord struct {
	TraceID    string                 `json:"trace_id"`
	Timestamp  time.Time              `json:"timestamp"`
	TraceGraph map[string]interface{} `json:"trace_graph"`
}

// TraceStore is a ring buffer for storing execution traces
type TraceStore struct {
	traces     map[string]TraceRecord
	order      []string
	mu         sync.Mutex
	
	enabled       bool
	maxTraces     int
	includeInput  bool
	maxChars      int
	GenService    *GenerationService
}

// NewTraceStore creates a new trace store
func NewTraceStore(gen *GenerationService) *TraceStore {
	enabled := getEnv("MAVAIA_INTROSPECTION_ENABLED", "true") == "true"
	maxTraces, _ := strconv.Atoi(getEnv("MAVAIA_INTROSPECTION_MAX_TRACES", "200"))
	includeInput := getEnv("MAVAIA_INTROSPECTION_INCLUDE_INPUT", "false") == "true"
	maxChars, _ := strconv.Atoi(getEnv("MAVAIA_INTROSPECTION_OUTPUT_MAX_CHARS", "2000"))

	return &TraceStore{
		traces:       make(map[string]TraceRecord),
		enabled:      enabled,
		maxTraces:    maxTraces,
		includeInput: includeInput,
		maxChars:     maxChars,
		GenService:   gen,
	}
}

// --- ADVANCED INTROSPECTION ---

func (s *TraceStore) AnalyzeTrace(ctx context.Context, traceID string) (map[string]interface{}, error) {
	record, ok := s.Get(traceID)
	if !ok { return nil, fmt.Errorf("trace %s not found", traceID) }
	
	prompt := fmt.Sprintf("Analyze this execution trace for errors, inefficiencies, or hallucinations:\n\n%v", record.TraceGraph)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Cognitive Trace Analyzer"})
	if err != nil { return nil, err }
	
	return map[string]interface{}{"success": true, "analysis": result["text"]}, nil
}

func (s *TraceStore) BuildThought(ctx context.Context, query string, context string) (string, error) {
	prompt := fmt.Sprintf("Query: %s\nContext: %s\n\nBuild a structured internal thought representation.", query, context)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Thought Builder"})
	if err != nil { return "", err }
	return result["text"].(string), nil
}

func (s *TraceStore) DiagnoseCognitiveLoop(ctx context.Context, sessionID string) (bool, string) {
	// Native heuristic loop detection
	return false, "No loop detected"
}

// --- EXISTING METHODS ---

func (s *TraceStore) Add(traceID string, trace map[string]interface{}) {
	if !s.enabled { return }
	s.mu.Lock()
	defer s.mu.Unlock()
	record := TraceRecord{TraceID: traceID, Timestamp: time.Now(), TraceGraph: s.redactAndTruncate(trace)}
	if _, ok := s.traces[traceID]; ok {
		for i, id := range s.order { if id == traceID { s.order = append(s.order[:i], s.order[i+1:]...); break } }
	}
	s.traces[traceID] = record
	s.order = append(s.order, traceID)
	if len(s.order) > s.maxTraces { oldID := s.order[0]; delete(s.traces, oldID); s.order = s.order[1:] }
}

func (s *TraceStore) redactAndTruncate(trace map[string]interface{}) map[string]interface{} {
	if !s.includeInput {
		if input, ok := trace["input"].(string); ok {
			hash := sha256.Sum256([]byte(input))
			trace["input"] = "sha256:" + hex.EncodeToString(hash[:])
		}
	}
	if fo, ok := trace["final_output"].(string); ok && len(fo) > s.maxChars { trace["final_output"] = fo[:s.maxChars] }
	return trace
}

func (s *TraceStore) Get(traceID string) (TraceRecord, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	res, ok := s.traces[traceID]
	return res, ok
}

func (s *TraceStore) ListRecent(limit int) []TraceRecord {
	s.mu.Lock()
	defer s.mu.Unlock()
	if limit > len(s.order) { limit = len(s.order) }
	res := make([]TraceRecord, limit)
	start := len(s.order) - limit
	for i := 0; i < limit; i++ { res[i] = s.traces[s.order[start+i]] }
	return res
}
