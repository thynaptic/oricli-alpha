package arc

import (
)

type Grid [][]int

func (g Grid) Height() int { return len(g) }
func (g Grid) Width() int { 
	if len(g) == 0 { return 0 }
	return len(g[0]) 
}

func (g Grid) Equals(other Grid) bool {
	if g.Height() != other.Height() || g.Width() != other.Width() {
		return false
	}
	for y := 0; y < g.Height(); y++ {
		for x := 0; x < g.Width(); x++ {
			if g[y][x] != other[y][x] {
				return false
			}
		}
	}
	return true
}

func (g Grid) Clone() Grid {
	newGrid := make(Grid, g.Height())
	for i := range g {
		newGrid[i] = make([]int, g.Width())
		copy(newGrid[i], g[i])
	}
	return newGrid
}

// Primitives for Transduction
func (g Grid) Rotate90() Grid {
	h, w := g.Height(), g.Width()
	newGrid := make(Grid, w)
	for i := 0; i < w; i++ {
		newGrid[i] = make([]int, h)
		for j := 0; j < h; j++ {
			newGrid[i][j] = g[h-1-j][i]
		}
	}
	return newGrid
}

func (g Grid) FlipHorizontal() Grid {
	h, w := g.Height(), g.Width()
	newGrid := make(Grid, h)
	for i := 0; i < h; i++ {
		newGrid[i] = make([]int, w)
		for j := 0; j < w; j++ {
			newGrid[i][j] = g[i][w-1-j]
		}
	}
	return newGrid
}

func (g Grid) FlipVertical() Grid {
	h, w := g.Height(), g.Width()
	newGrid := make(Grid, h)
	for i := 0; i < h; i++ {
		newGrid[i] = make([]int, w)
		copy(newGrid[i], g[h-1-i])
	}
	return newGrid
}

func (g Grid) ReplaceColor(from, to int) Grid {
	newGrid := g.Clone()
	for y := 0; y < g.Height(); y++ {
		for x := 0; x < g.Width(); x++ {
			if newGrid[y][x] == from {
				newGrid[y][x] = to
			}
		}
	}
	return newGrid
}

type Task struct {
	Train []struct {
		Input  Grid
		Output Grid
	}
	Test []struct {
		Input Grid
	}
}
