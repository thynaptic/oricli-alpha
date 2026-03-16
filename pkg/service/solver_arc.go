package service

import (
	"fmt"
)

type Grid [][]int

type ARCProblem struct {
	Train []struct {
		Input  Grid `json:"input"`
		Output Grid `json:"output"`
	} `json:"train"`
	Test []struct {
		Input  Grid `json:"input"`
		Output Grid `json:"output,omitempty"`
	} `json:"test"`
}

type ARCSolver struct{}

func NewARCSolver() *ARCSolver {
	return &ARCSolver{}
}

// Solve tries to find a transformation rule from Train and apply it to Test
func (s *ARCSolver) Solve(problem ARCProblem) (Grid, error) {
	if len(problem.Train) == 0 || len(problem.Test) == 0 {
		return nil, fmt.Errorf("invalid ARC problem format")
	}

	transforms := []func(Grid) Grid{
		s.Rotate90,
		s.Rotate180,
		s.Rotate270,
		s.FlipH,
		s.FlipV,
	}

	var validTransform func(Grid) Grid

	// 2. Test which transform works for ALL training examples
	for _, transformFunc := range transforms {
		valid := true
		for _, ex := range problem.Train {
			res := transformFunc(ex.Input)
			if !s.GridsEqual(res, ex.Output) {
				valid = false
				break
			}
		}
		if valid {
			validTransform = transformFunc
			break
		}
	}

	// 3. Apply to Test
	if validTransform != nil {
		return validTransform(problem.Test[0].Input), nil
	}

	return nil, fmt.Errorf("no simple transformation rule found")
}

// -- Basic Transformations --

func (s *ARCSolver) Rotate90(g Grid) Grid {
	if len(g) == 0 { return nil }
	rows, cols := len(g), len(g[0])
	res := make(Grid, cols)
	for i := range res {
		res[i] = make([]int, rows)
		for j := range res[i] {
			res[i][j] = g[rows-1-j][i]
		}
	}
	return res
}

func (s *ARCSolver) Rotate180(g Grid) Grid {
	return s.Rotate90(s.Rotate90(g))
}

func (s *ARCSolver) Rotate270(g Grid) Grid {
	return s.Rotate90(s.Rotate180(g))
}

func (s *ARCSolver) FlipH(g Grid) Grid {
	if len(g) == 0 { return nil }
	rows, cols := len(g), len(g[0])
	res := make(Grid, rows)
	for i := range res {
		res[i] = make([]int, cols)
		for j := range res[i] {
			res[i][j] = g[i][cols-1-j]
		}
	}
	return res
}

func (s *ARCSolver) FlipV(g Grid) Grid {
	if len(g) == 0 { return nil }
	rows, cols := len(g), len(g[0])
	res := make(Grid, rows)
	for i := range res {
		res[i] = make([]int, cols)
		for j := range res[i] {
			res[i][j] = g[rows-1-i][j]
		}
	}
	return res
}

func (s *ARCSolver) GridsEqual(g1, g2 Grid) bool {
	if len(g1) != len(g2) { return false }
	if len(g1) > 0 && len(g1[0]) != len(g2[0]) { return false }
	for i := range g1 {
		for j := range g1[i] {
			if g1[i][j] != g2[i][j] { return false }
		}
	}
	return true
}
