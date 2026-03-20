package service

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/arc"
	"github.com/thynaptic/oricli-go/pkg/cognition"
)

// ARCSolverService provides Go-native logic for solving ARC tasks using MCTS
type ARCSolverService struct {
	genService *GenerationService
	orch       *GoOrchestrator
}

func NewARCSolverService(genService *GenerationService, orch *GoOrchestrator) *ARCSolverService {
	return &ARCSolverService{
		genService: genService,
		orch:       orch,
	}
}

func (s *ARCSolverService) SolveTask(ctx context.Context, task arc.Task) (*arc.ARCResult, error) {
	log.Printf("[ARCSolver] Starting deep search for task with %d examples", len(task.Train))

	// Define MCTS callbacks
	callbacks := cognition.MCTSCallbacks{
		ProposeBranches: func(ctx context.Context, currentPath string, count int) ([]string, error) {
			// Ask Ministral to propose transformation steps based on current path and examples
			prompt := fmt.Sprintf("ARC Task Examples: %v\nCurrent Transformation Path: %s\nPropose %d next transformation steps (e.g., 'Rotate90', 'FlipH', 'ReplaceColor(1,2)').", task.Train, currentPath, count)
			res, err := s.genService.Generate(prompt, nil)
			if err != nil {
				return nil, err
			}
			// Parse proposed steps (simplified)
			steps := strings.Split(res["text"].(string), "\n")
			return steps, nil
		},
		EvaluatePath: func(ctx context.Context, path string) (cognition.MCTSEvaluation, error) {
			// Execute the path on training inputs and compare with outputs
			score := s.evaluateTransformationPath(task, path)
			return cognition.MCTSEvaluation{
				Confidence: score,
				Terminal:   score == 1.0,
				Reason:     fmt.Sprintf("Path matched %f percent of pixels", score*100),
			}, nil
		},
		AdversarialEval: func(ctx context.Context, path string) (cognition.MCTSEvaluation, error) {
			// Red-team check: does this path make sense? 
			// For ARC, we just use the same evaluation for now
			score := s.evaluateTransformationPath(task, path)
			return cognition.MCTSEvaluation{
				Confidence: score,
				Terminal:   score == 1.0,
			}, nil
		},
	}

	engine := &cognition.MCTSEngine{
		Config: cognition.MCTSConfig{
			Iterations:   10,
			BranchFactor: 3,
			RolloutDepth: 4,
		},
		Callbacks: callbacks,
	}

	result, err := engine.SearchV2(ctx, "Root")
	if err != nil {
		return nil, err
	}

	// Apply best path to test input
	prediction := s.applyPath(task.Test[0].Input, result.Answer)

	return &arc.ARCResult{
		Prediction: prediction,
		Confidence: result.BestScore,
		Method:     "go_native_mcts_induction",
		Program:    result.Answer,
	}, nil
}

func (s *ARCSolverService) evaluateTransformationPath(task arc.Task, path string) float64 {
	totalPixels := 0
	matchedPixels := 0

	for _, ex := range task.Train {
		result := s.applyPath(ex.Input, path)
		if result.Height() != ex.Output.Height() || result.Width() != ex.Output.Width() {
			continue
		}
		for y := 0; y < result.Height(); y++ {
			for x := 0; x < result.Width(); x++ {
				totalPixels++
				if result[y][x] == ex.Output[y][x] {
					matchedPixels++
				}
			}
		}
	}

	if totalPixels == 0 {
		return 0
	}
	return float64(matchedPixels) / float64(totalPixels)
}

func (s *ARCSolverService) applyPath(input arc.Grid, path string) arc.Grid {
	steps := strings.Split(path, "->")
	current := input.Clone()
	for _, step := range steps {
		step = strings.TrimSpace(step)
		switch step {
		case "Rotate90":
			current = current.Rotate90()
		case "FlipH":
			current = current.FlipHorizontal()
		case "FlipV":
			current = current.FlipVertical()
		// Add more primitives as needed
		}
	}
	return current
}
