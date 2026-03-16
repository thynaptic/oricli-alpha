package service

import (
	"fmt"
)

// ZebraConstraint represents a logical rule in the puzzle
type ZebraConstraint struct {
	Type   string   `json:"type"`   // "same", "next_to", "left_of", "position"
	Value1 string   `json:"value1"`
	Value2 string   `json:"value2"`
	Pos    int      `json:"pos"`    // Used for "position" type
}

// ZebraPuzzle represents the entities and rules
type ZebraPuzzle struct {
	Categories  map[string][]string `json:"categories"` // e.g., "color" -> ["red", "green"]
	Constraints []ZebraConstraint   `json:"constraints"`
	NumHouses   int                 `json:"num_houses"`
}

// ZebraSolver is a backtracking solver for constraint satisfaction
type ZebraSolver struct {
	Puzzle ZebraPuzzle
}

func NewZebraSolver(p ZebraPuzzle) *ZebraSolver {
	if p.NumHouses == 0 {
		p.NumHouses = 5
	}
	return &ZebraSolver{Puzzle: p}
}

// Solution is house_index -> category -> value
type ZebraSolution map[int]map[string]string

func (s *ZebraSolver) Solve() (ZebraSolution, error) {
	solution := make(ZebraSolution)
	for i := 1; i <= s.Puzzle.NumHouses; i++ {
		solution[i] = make(map[string]string)
	}

	if s.backtrack(solution, 1, s.getCategoryList()[0]) {
		return solution, nil
	}

	return nil, fmt.Errorf("no solution found")
}

func (s *ZebraSolver) getCategoryList() []string {
	var cats []string
	for cat := range s.Puzzle.Categories {
		cats = append(cats, cat)
	}
	return cats
}

func (s *ZebraSolver) backtrack(sol ZebraSolution, house int, cat string) bool {
	// 1. Base case: all houses and categories filled
	if house > s.Puzzle.NumHouses {
		return true
	}

	// 2. Determine next house/category
	cats := s.getCategoryList()
	nextHouse := house
	nextCat := ""
	for i, c := range cats {
		if c == cat {
			if i+1 < len(cats) {
				nextCat = cats[i+1]
			} else {
				nextHouse = house + 1
				if nextHouse <= s.Puzzle.NumHouses {
					nextCat = cats[0]
				}
			}
			break
		}
	}

	// 3. Try all possible values for current house/category
	for _, val := range s.Puzzle.Categories[cat] {
		if s.isPossible(sol, house, cat, val) {
			sol[house][cat] = val
			
			// If all constraints satisfied so far, recurse
			if s.checkConstraints(sol) {
				if nextHouse > s.Puzzle.NumHouses || s.backtrack(sol, nextHouse, nextCat) {
					return true
				}
			}
			
			delete(sol[house], cat)
		}
	}

	return false
}

func (s *ZebraSolver) isPossible(sol ZebraSolution, house int, cat, val string) bool {
	// Check if value already used in this category
	for i := 1; i <= s.Puzzle.NumHouses; i++ {
		if sol[i][cat] == val {
			return false
		}
	}
	return true
}

func (s *ZebraSolver) checkConstraints(sol ZebraSolution) bool {
	for _, c := range s.Puzzle.Constraints {
		switch c.Type {
		case "position":
			// Value1 must be at house c.Pos
			if v, ok := sol[c.Pos][s.findCategory(c.Value1)]; ok {
				if v != c.Value1 { return false }
			}
		case "same":
			// If both values assigned, they must be in same house
			p1 := s.findPosition(sol, c.Value1)
			p2 := s.findPosition(sol, c.Value2)
			if p1 != 0 && p2 != 0 && p1 != p2 { return false }
		case "left_of":
			p1 := s.findPosition(sol, c.Value1)
			p2 := s.findPosition(sol, c.Value2)
			if p1 != 0 && p2 != 0 && p1 != p2-1 { return false }
		case "next_to":
			p1 := s.findPosition(sol, c.Value1)
			p2 := s.findPosition(sol, c.Value2)
			if p1 != 0 && p2 != 0 {
				diff := p1 - p2
				if diff != 1 && diff != -1 { return false }
			}
		}
	}
	return true
}

func (s *ZebraSolver) findCategory(val string) string {
	for cat, vals := range s.Puzzle.Categories {
		for _, v := range vals {
			if v == val { return cat }
		}
	}
	return ""
}

func (s *ZebraSolver) findPosition(sol ZebraSolution, val string) int {
	cat := s.findCategory(val)
	if cat == "" { return 0 }
	for i := 1; i <= s.Puzzle.NumHouses; i++ {
		if sol[i][cat] == val { return i }
	}
	return 0
}
