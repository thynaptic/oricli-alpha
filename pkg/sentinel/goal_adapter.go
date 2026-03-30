package sentinel

import (
	"context"

	"github.com/thynaptic/oricli-go/pkg/goal"
)

// GoalAdapter wraps AdversarialSentinel to satisfy the goal.SentinelChallenger
// interface, converting between sentinel.SentinelReport and goal.SentinelReport.
type GoalAdapter struct {
	inner *AdversarialSentinel
}

// NewGoalAdapter creates a GoalAdapter wrapping the given sentinel.
func NewGoalAdapter(s *AdversarialSentinel) *GoalAdapter {
	return &GoalAdapter{inner: s}
}

// Challenge satisfies goal.SentinelChallenger.
func (a *GoalAdapter) Challenge(ctx context.Context, query, plan string) goal.SentinelReport {
	r := a.inner.Challenge(ctx, query, plan)

	vs := make([]goal.SentinelViolation, len(r.Violations))
	for i, v := range r.Violations {
		vs[i] = goal.SentinelViolation{
			Type:        string(v.Type),
			Description: v.Description,
			Severity:    string(v.Severity),
		}
	}
	return goal.SentinelReport{
		Passed:      r.Passed,
		Blocked:     r.Blocked,
		Violations:  vs,
		RevisedPlan: r.RevisedPlan,
	}
}
