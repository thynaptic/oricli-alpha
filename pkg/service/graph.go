package service

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// GraphService manages Neo4j connections and high-level graph operations in Go
type GraphService struct {
	Driver neo4j.DriverWithContext
}

func NewGraphService() (*GraphService, error) {
	uri := os.Getenv("NEO4J_URI")
	if uri == "" {
		uri = "bolt://localhost:7687"
	}
	user := os.Getenv("NEO4J_USER")
	if user == "" {
		user = "neo4j"
	}
	password := os.Getenv("NEO4J_PASSWORD")
	if password == "" {
		password = "password"
	}

	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(user, password, ""))
	if err != nil {
		return nil, fmt.Errorf("failed to create Neo4j driver: %w", err)
	}

	ctx := context.Background()
	if err := driver.VerifyConnectivity(ctx); err != nil {
		return nil, fmt.Errorf("failed to connect to Neo4j at %s: %w", uri, err)
	}

	log.Printf("[GraphService] Connected to Neo4j at %s", uri)
	return &GraphService{Driver: driver}, nil
}

func (s *GraphService) ExecuteQuery(query string, params map[string]interface{}) ([]map[string]interface{}, error) {
	if s == nil || s.Driver == nil {
		return nil, fmt.Errorf("graph service unavailable (Neo4j not connected)")
	}
	ctx := context.Background()
	session := s.Driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	result, err := session.Run(ctx, query, params)
	if err != nil {
		return nil, err
	}

	var records []map[string]interface{}
	for result.Next(ctx) {
		records = append(records, result.Record().AsMap())
	}

	return records, result.Err()
}

func (s *GraphService) AddNode(label string, properties map[string]interface{}) (bool, error) {
	id, ok := properties["id"].(string)
	if !ok || id == "" {
		return false, fmt.Errorf("node must have a non-empty 'id' property")
	}

	query := fmt.Sprintf("MERGE (n:%s {id: $id}) SET n += $props RETURN n", label)
	params := map[string]interface{}{
		"id":    id,
		"props": properties,
	}

	res, err := s.ExecuteQuery(query, params)
	if err != nil {
		return false, err
	}

	return len(res) > 0, nil
}

func (s *GraphService) AddRelationship(sourceID, targetID, relType string, props map[string]interface{}) (bool, error) {
	query := fmt.Sprintf(`
		MATCH (a {id: $source_id}), (b {id: $target_id})
		MERGE (a)-[r:%s]->(b)
		SET r += $props
		RETURN r
	`, relType)

	params := map[string]interface{}{
		"source_id": sourceID,
		"target_id": targetID,
		"props":     props,
	}

	res, err := s.ExecuteQuery(query, params)
	if err != nil {
		return false, err
	}

	return len(res) > 0, nil
}

func (s *GraphService) FindPath(startID, endID string, maxDepth int) ([]map[string]interface{}, error) {
	query := fmt.Sprintf(`
		MATCH (start {id: $start_id}), (end {id: $end_id}),
		p = shortestPath((start)-[*..%d]->(end))
		RETURN p
	`, maxDepth)

	params := map[string]interface{}{
		"start_id": startID,
		"end_id":   endID,
	}

	return s.ExecuteQuery(query, params)
}

func (s *GraphService) GetNeighbors(nodeID string, depth int) ([]map[string]interface{}, error) {
	query := fmt.Sprintf(`
		MATCH (n {id: $node_id})-[r*..%d]-(m)
		RETURN m, r
	`, depth)

	params := map[string]interface{}{
		"node_id": nodeID,
	}

	return s.ExecuteQuery(query, params)
}

func (s *GraphService) Close() {
	if s.Driver != nil {
		s.Driver.Close(context.Background())
	}
}
