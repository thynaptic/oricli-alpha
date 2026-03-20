package cognition

import (
	"time"
)

// --- Pillar 35: Symbolic Reasoning Models ---
// Ported from Aurora's SymbolicReasoningModels.swift.
// Defines formal schemas for SAT, SMT, and CSP solvers.

type ProblemType string

const (
	TypeSAT              ProblemType = "sat"
	TypeSMT              ProblemType = "smt"
	TypeCSP              ProblemType = "csp"
	TypeLogicProg        ProblemType = "logic_programming"
	TypeSymbolicMath     ProblemType = "symbolic_math"
	TypeVerification     ProblemType = "verification"
)

type ExpressionType string

const (
	ExpPropositional  ExpressionType = "propositional"
	ExpFirstOrder     ExpressionType = "first_order"
	ExpConstraint     ExpressionType = "constraint"
	ExpMathematical   ExpressionType = "mathematical"
)

type SymbolicExpression struct {
	ID         string         `json:"id"`
	Expression string         `json:"expression"`
	Type       ExpressionType `json:"type"`
	Variables  []string       `json:"variables"`
}

type ConstraintType string

const (
	ConEquality   ConstraintType = "equality"
	ConInequality ConstraintType = "inequality"
	ConLogical    ConstraintType = "logical"
	ConTemporal   ConstraintType = "temporal"
)

type Constraint struct {
	ID         string         `json:"id"`
	Expression string         `json:"expression"`
	Type       ConstraintType `json:"type"`
	Priority   float64        `json:"priority"`
	IsHard     bool           `json:"is_hard"`
}

type SymbolicProblem struct {
	ID          string               `json:"id"`
	Query       string               `json:"query"`
	Type        ProblemType          `json:"type"`
	Expressions []SymbolicExpression `json:"expressions"`
	Constraints []Constraint         `json:"constraints"`
	Timestamp   time.Time            `json:"timestamp"`
}

type SymbolicSolution struct {
	ProblemID     string            `json:"problem_id"`
	IsSatisfiable bool              `json:"is_satisfiable"`
	Model         map[string]string `json:"model,omitempty"`
	Proof         string            `json:"proof,omitempty"`
	Solver        string            `json:"solver"`
	Confidence    float64           `json:"confidence"`
	Latency       time.Duration     `json:"latency"`
}
