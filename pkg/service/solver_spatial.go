package service

import (
	"fmt"
	"math"
	"strings"
)

// SpatialRelation represents a relative position between two entities
type SpatialRelation struct {
	Entity1  string `json:"entity1"`
	Relation string `json:"relation"` // "left_of", "right_of", "above", "below"
	Entity2  string `json:"entity2"`
}

// SpatialProblem represents the parsed spatial puzzle
type SpatialProblem struct {
	Entities  []string          `json:"entities"`
	Relations []SpatialRelation `json:"relations"`
	GridSize  int               `json:"grid_size"` // e.g., 3 for a 3x3 grid
	Question  string            `json:"question"`  // e.g., "What is at (0, 0)?" or "Where is the apple?"
}

type Point struct {
	X int
	Y int
}

// SpatialSolver resolves spatial constraint puzzles natively
type SpatialSolver struct {
	Problem SpatialProblem
}

func NewSpatialSolver(p SpatialProblem) *SpatialSolver {
	if p.GridSize == 0 {
		p.GridSize = int(math.Ceil(math.Sqrt(float64(len(p.Entities)))))
		if p.GridSize < 3 {
			p.GridSize = 3 // Default minimum
		}
	}
	return &SpatialSolver{Problem: p}
}

// Solve returns the coordinate mapping for all entities
func (s *SpatialSolver) Solve() (map[string]Point, error) {
	assignments := make(map[string]Point)
	
	if s.backtrack(assignments, 0) {
		return assignments, nil
	}
	
	return nil, fmt.Errorf("no valid spatial arrangement found")
}

func (s *SpatialSolver) backtrack(assignments map[string]Point, entityIdx int) bool {
	if entityIdx >= len(s.Problem.Entities) {
		return true // All placed
	}

	entity := s.Problem.Entities[entityIdx]
	size := s.Problem.GridSize

	for y := 0; y < size; y++ {
		for x := 0; x < size; x++ {
			pt := Point{X: x, Y: y}
			
			// Check if space is occupied
			occupied := false
			for _, existingPt := range assignments {
				if existingPt.X == x && existingPt.Y == y {
					occupied = true
					break
				}
			}
			
			if !occupied {
				assignments[entity] = pt
				if s.checkConstraints(assignments) {
					if s.backtrack(assignments, entityIdx+1) {
						return true
					}
				}
				delete(assignments, entity) // backtrack
			}
		}
	}

	return false
}

func (s *SpatialSolver) checkConstraints(assignments map[string]Point) bool {
	for _, rel := range s.Problem.Relations {
		p1, ok1 := assignments[rel.Entity1]
		p2, ok2 := assignments[rel.Entity2]
		
		// Only check if BOTH entities are currently placed
		if ok1 && ok2 {
			switch rel.Relation {
			case "left_of":
				if p1.X >= p2.X || p1.Y != p2.Y { return false }
			case "right_of":
				if p1.X <= p2.X || p1.Y != p2.Y { return false }
			case "above":
				if p1.Y >= p2.Y || p1.X != p2.X { return false }
			case "below":
				if p1.Y <= p2.Y || p1.X != p2.X { return false }
			case "next_to":
				dist := math.Abs(float64(p1.X-p2.X)) + math.Abs(float64(p1.Y-p2.Y))
				if dist != 1 { return false }
			}
		}
	}
	return true
}

func (s *SpatialSolver) AnswerQuestion(assignments map[string]Point) string {
	// Simple resolution logic for common spatial questions
	q := s.Problem.Question
	
	// If asking "Where is X?"
	for _, e := range s.Problem.Entities {
		if strings.Contains(q, e) {
			if pt, ok := assignments[e]; ok {
				return fmt.Sprintf("%s is at (%d, %d).", e, pt.X, pt.Y)
			}
		}
	}
	
	return "Could not determine answer from spatial map."
}
