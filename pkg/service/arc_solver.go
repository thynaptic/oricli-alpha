package service

import (
	"context"
	"time"
)

// ARCTask represents an ARC task with training examples and test input
type ARCTask struct {
	TrainInputs  [][][]int `json:"train_inputs"`
	TrainOutputs [][][]int `json:"train_outputs"`
	TestInput    [][]int   `json:"test_input"`
}

// ARCResult represents the result of an ARC solve attempt
type ARCResult struct {
	Prediction [][]int `json:"prediction"`
	Confidence float64 `json:"confidence"`
	Method     string  `json:"method"`
	Program    string  `json:"program,omitempty"`
}

// ARCSolverService provides Go-native logic for solving ARC tasks
type ARCSolverService struct {
	genService *GenerationService
	orch       *GoOrchestrator
}

// NewARCSolverService creates a new ARC solver service
func NewARCSolverService(genService *GenerationService, orch *GoOrchestrator) *ARCSolverService {
	return &ARCSolverService{
		genService: genService,
		orch:       orch,
	}
}

// SolveTask coordinates induction and transduction to solve an ARC task
func (s *ARCSolverService) SolveTask(ctx context.Context, task ARCTask) (*ARCResult, error) {
	// 1. Try Transduction (Geometric/Color logic) - High Speed
	res, err := s.Transduce(ctx, task)
	if err == nil && res.Confidence > 0.9 {
		return res, nil
	}

	// 2. Try Induction (Program Synthesis via LLM) - Slower but powerful
	indRes, err := s.Induce(ctx, task)
	if err == nil {
		return indRes, nil
	}

	return res, err
}

// Transduce performs pattern matching and geometric transformations
func (s *ARCSolverService) Transduce(ctx context.Context, task ARCTask) (*ARCResult, error) {
	// For now, proxy to Python which has numpy/scipy logic
	// In a real EPYC VPS optimized scenario, we'd use gonum/mat here
	result, err := s.orch.Execute("arc_transduction.predict", map[string]interface{}{"task": task}, 30*time.Second)
	if err != nil {
		return nil, err
	}

	resMap := result.(map[string]interface{})
	
	// Complex cast back to [][]int
	predRaw, _ := resMap["prediction"].([]interface{})
	prediction := s.castGrid(predRaw)
	
	conf, _ := resMap["confidence"].(float64)

	return &ARCResult{
		Prediction: prediction,
		Confidence: conf,
		Method:     "transduction",
	}, nil
}

// Induce performs program synthesis via LLM
func (s *ARCSolverService) Induce(ctx context.Context, task ARCTask) (*ARCResult, error) {
	// Proxy to Python which handles the synthesis loop and code verification
	result, err := s.orch.Execute("arc_induction.solve_task", map[string]interface{}{"task": task}, 120*time.Second)
	if err != nil {
		return nil, err
	}

	resMap := result.(map[string]interface{})
	predRaw, _ := resMap["prediction"].([]interface{})
	prediction := s.castGrid(predRaw)
	
	conf, _ := resMap["confidence"].(float64)
	prog, _ := resMap["program"].(string)

	return &ARCResult{
		Prediction: prediction,
		Confidence: conf,
		Method:     "induction",
		Program:    prog,
	}, nil
}

func (s *ARCSolverService) castGrid(raw []interface{}) [][]int {
	grid := make([][]int, len(raw))
	for i, r := range raw {
		rowRaw, _ := r.([]interface{})
		grid[i] = make([]int, len(rowRaw))
		for j, v := range rowRaw {
			grid[i][j] = int(ToFloat64(v))
		}
	}
	return grid
}
