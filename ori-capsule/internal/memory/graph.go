package memory

import (
	"strings"
	"sync"
	"time"
)

// GraphNode is a session working-memory node (in-process only — no Neo4j).
type GraphNode struct {
	ID        string
	Type      string
	Content   string
	SessionID string
	At        time.Time
}

type GraphEdge struct {
	Source   string
	Target   string
	Type     string
	Strength float64
}

// WorkingGraph is the session-scoped entity graph. Never blocks on I/O.
type WorkingGraph struct {
	mu    sync.RWMutex
	nodes map[string]*GraphNode
	edges map[string][]*GraphEdge
}

func NewWorkingGraph() *WorkingGraph {
	return &WorkingGraph{
		nodes: make(map[string]*GraphNode),
		edges: make(map[string][]*GraphEdge),
	}
}

func (g *WorkingGraph) AddNode(n *GraphNode) {
	if n == nil || n.ID == "" {
		return
	}
	if n.At.IsZero() {
		n.At = time.Now()
	}
	g.mu.Lock()
	g.nodes[n.ID] = n
	g.mu.Unlock()
}

func (g *WorkingGraph) AddEdge(e *GraphEdge) {
	if e == nil || e.Source == "" || e.Target == "" {
		return
	}
	g.mu.Lock()
	g.edges[e.Source] = append(g.edges[e.Source], e)
	g.mu.Unlock()
}

// NoteTurn records a lightweight topic node from a user turn (keyword extract).
func (g *WorkingGraph) NoteTurn(sessionID, content string) {
	topic := extractTopic(content)
	if topic == "" {
		return
	}
	id := sessionID + ":" + strings.ReplaceAll(topic, " ", "_")
	g.AddNode(&GraphNode{
		ID:        id,
		Type:      "topic",
		Content:   topic,
		SessionID: sessionID,
	})
}

// KeywordHits returns up to limit nodes whose content overlaps query words.
func (g *WorkingGraph) KeywordHits(query string, limit int) []*GraphNode {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if limit <= 0 {
		limit = 5
	}
	words := strings.Fields(strings.ToLower(query))
	var hits []*GraphNode
	for _, n := range g.nodes {
		score := 0
		lower := strings.ToLower(n.Content)
		for _, w := range words {
			if len(w) > 2 && strings.Contains(lower, w) {
				score++
			}
		}
		if score > 0 {
			hits = append(hits, n)
			if len(hits) >= limit {
				break
			}
		}
	}
	return hits
}

func (g *WorkingGraph) NodeCount() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return len(g.nodes)
}
