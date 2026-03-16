package service

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// SolverStatus represents the current state of a symbolic solver
type SolverStatus string

const (
	SolverReady       SolverStatus = "ready"
	SolverUnavailable SolverStatus = "unavailable"
	SolverError       SolverStatus = "error"
)

// SolverInfo provides metadata about a solver
type SolverInfo struct {
	Name          string       `json:"name"`
	Status        SolverStatus `json:"status"`
	IsAvailable   bool         `json:"is_available"`
	Error         string       `json:"error,omitempty"`
	LastUsed      time.Time    `json:"last_used,omitempty"`
}

// SymbolicSolution represents the output of a solver
type SymbolicSolution struct {
	IsSatisfiable bool                   `json:"is_satisfiable"`
	Model         map[string]interface{} `json:"model,omitempty"`
	ExecutionTime time.Duration          `json:"execution_time"`
	SolverUsed    string                 `json:"solver_used"`
	Error         string                 `json:"error,omitempty"`
}

// SymbolicSolverManager manages the lifecycle of various solvers
type SymbolicSolverManager struct {
	solvers map[string]SolverInfo
	orch    *GoOrchestrator
	mu      sync.RWMutex
}

// NewSymbolicSolverManager creates a new solver manager
func NewSymbolicSolverManager(orch *GoOrchestrator) *SymbolicSolverManager {
	m := &SymbolicSolverManager{
		solvers: make(map[string]SolverInfo),
		orch:    orch,
	}
	m.initDefaultSolvers()
	return m
}

func (m *SymbolicSolverManager) initDefaultSolvers() {
	// These will initially be proxied to Python
	m.solvers["z3"] = SolverInfo{Name: "z3", Status: SolverReady, IsAvailable: true}
	m.solvers["pysat"] = SolverInfo{Name: "pysat", Status: SolverReady, IsAvailable: true}
	m.solvers["sympy"] = SolverInfo{Name: "sympy", Status: SolverReady, IsAvailable: true}
	m.solvers["prolog"] = SolverInfo{Name: "prolog", Status: SolverReady, IsAvailable: true}
}

// Solve routes a problem to the best available solver
func (m *SymbolicSolverManager) Solve(ctx context.Context, problem map[string]interface{}) (*SymbolicSolution, error) {
	problemType, _ := problem["problem_type"].(string)
	solverName := m.SelectSolver(problemType)
	
	if solverName == "" {
		return nil, fmt.Errorf("no suitable solver found for problem type: %s", problemType)
	}

	start := time.Now()
	
	// Proxy to Python Sidecar via Orchestrator
	// The Python sidecar will use the legacy symbolic_solvers package
	result, err := m.orch.Execute(fmt.Sprintf("symbolic_solver.%s_solve", solverName), problem, 30*time.Second)
	
	if err != nil {
		return &SymbolicSolution{
			SolverUsed:    solverName,
			ExecutionTime: time.Since(start),
			Error:         err.Error(),
		}, err
	}

	resMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid response format from solver")
	}

	m.mu.Lock()
	info := m.solvers[solverName]
	info.LastUsed = time.Now()
	m.solvers[solverName] = info
	m.mu.Unlock()

	isSat, _ := resMap["is_satisfiable"].(bool)
	model, _ := resMap["model"].(map[string]interface{})

	return &SymbolicSolution{
		IsSatisfiable: isSat,
		Model:         model,
		ExecutionTime: time.Since(start),
		SolverUsed:    solverName,
	}, nil
}

// SelectSolver picks the best solver for a given problem type
func (m *SymbolicSolverManager) SelectSolver(problemType string) string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	switch problemType {
	case "sat":
		return m.firstAvailable("pysat", "z3")
	case "smt", "csp", "verification":
		return m.firstAvailable("z3")
	case "symbolic_math":
		return m.firstAvailable("sympy")
	case "logic_programming":
		return m.firstAvailable("prolog")
	default:
		return m.firstAvailable("z3")
	}
}

func (m *SymbolicSolverManager) firstAvailable(names ...string) string {
	for _, name := range names {
		if info, ok := m.solvers[name]; ok && info.IsAvailable {
			return name
		}
	}
	return ""
}

// GetSolverStatuses returns the status of all managed solvers
func (m *SymbolicSolverManager) GetSolverStatuses() []SolverInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()
	
	res := make([]SolverInfo, 0, len(m.solvers))
	for _, info := range m.solvers {
		res = append(res, info)
	}
	return res
}
