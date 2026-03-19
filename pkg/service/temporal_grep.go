package service

import (
	"context"
	"fmt"
	"strings"
)

// TemporalGrepService allows agents to perform keyword searches over chronological memory slices.
type TemporalGrepService struct {
	Memory *MemoryBridge
}

// NewTemporalGrepService creates a new grep service for temporal memory.
func NewTemporalGrepService(mb *MemoryBridge) *TemporalGrepService {
	return &TemporalGrepService{Memory: mb}
}

// Grep searches for a keyword within a specific time window.
func (s *TemporalGrepService) Grep(ctx context.Context, keyword string, startTime, endTime float64) ([]MemoryRecord, error) {
	records, err := s.Memory.QueryTemporal(startTime, endTime)
	if err != nil {
		return nil, err
	}

	var matched []MemoryRecord
	keyword = strings.ToLower(keyword)

	for _, rec := range records {
		found := false
		
		// 1. Search in Data fields
		for _, v := range rec.Data {
			if strings.Contains(strings.ToLower(fmt.Sprintf("%v", v)), keyword) {
				found = true
				break
			}
		}
		
		if !found {
			// 2. Search in Metadata fields
			for _, v := range rec.Metadata {
				if strings.Contains(strings.ToLower(fmt.Sprintf("%v", v)), keyword) {
					found = true
					break
				}
			}
		}

		if found {
			matched = append(matched, rec)
		}
	}

	return matched, nil
}
