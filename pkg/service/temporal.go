package service

import (
	"fmt"
	"time"
)

type TemporalService struct {
	Graph *GraphService
}

func NewTemporalService(graph *GraphService) *TemporalService {
	return &TemporalService{Graph: graph}
}

func (s *TemporalService) RecordEvent(eventType string, description string, metadata map[string]interface{}) (string, error) {
	eventID := fmt.Sprintf("event-%d", time.Now().UnixNano())
	timestamp := time.Now().Format(time.RFC3339)

	properties := map[string]interface{}{
		"id":          eventID,
		"type":        eventType,
		"description": description,
		"timestamp":   timestamp,
	}
	for k, v := range metadata {
		properties[k] = v
	}

	// 1. Create the Event Node
	_, err := s.Graph.AddNode("Event", properties)
	if err != nil {
		return "", err
	}

	// 2. Link to Timeline (Linked List of Events)
	query := `
		MATCH (e:Event {id: $event_id})
		MATCH (last:Event) WHERE last.id <> $event_id
		WITH e, last ORDER BY last.timestamp DESC LIMIT 1
		MERGE (last)-[r:CHRONO_NEXT]->(e)
		RETURN e.id
	`
	params := map[string]interface{}{"event_id": eventID}
	_, err = s.Graph.ExecuteQuery(query, params)
	
	return eventID, err
}

func (s *TemporalService) GetRecentHistory(limit int) ([]map[string]interface{}, error) {
	query := `
		MATCH (e:Event)
		RETURN e ORDER BY e.timestamp DESC LIMIT $limit
	`
	params := map[string]interface{}{"limit": limit}
	return s.Graph.ExecuteQuery(query, params)
}
