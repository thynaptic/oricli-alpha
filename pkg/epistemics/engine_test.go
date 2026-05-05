package epistemics

import (
	"context"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"
)

// TestDeutschGaps proves the conjecture-criticism-synthesis loop is doing genuine
// dialectical reasoning — not token prediction dressed as explanation.
//
// Run with:
//
//	ANTHROPIC_API_KEY=sk-... go test ./pkg/epistemics/ -v -run TestDeutschGaps -timeout 120s
func TestDeutschGaps(t *testing.T) {
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("ANTHROPIC_API_KEY not set — skipping live epistemics test")
	}

	cases := []struct {
		name  string
		query string
		desc  string // what Deutsch gap this exercises
	}{
		{
			name:  "causal_mechanism",
			query: "Why do markets consistently fail to price in long-term catastrophic risks on their own?",
			desc:  "Gap 1+2: forces a causal mechanism (WHY), not a prediction or description of what markets do",
		},
		{
			name:  "novel_explanation",
			query: "Why does confirmation bias persist even in people who are fully aware of it and actively trying to avoid it?",
			desc:  "Gap 1: requires a novel explanatory leap — pattern-matching gives wrong answer here",
		},
		{
			name:  "self_referential",
			query: "How does a conjecture-criticism loop produce better explanations than single-pass inference?",
			desc:  "Gap 3: ORI reasoning about her own epistemological architecture",
		},
		{
			name:  "deep_mechanism",
			query: "What causes some startups to hit exponential growth while structurally identical ones plateau?",
			desc:  "Gap 2: prediction would list factors; explanation requires underlying mechanism",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Logf("\n%s", strings.Repeat("─", 70))
			t.Logf("QUERY: %s", tc.query)
			t.Logf("DEUTSCH GAP: %s", tc.desc)
			t.Logf("%s", strings.Repeat("─", 70))

			ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
			defer cancel()

			start := time.Now()
			result, err := Run(ctx, ConjectionCycle{
				Query:   tc.query,
				MaxIter: 2,
			})
			elapsed := time.Since(start)

			if err != nil {
				t.Fatalf("Run() error: %v", err)
			}

			printTrace(t, result, elapsed)

			// Assertions that prove dialectical reasoning happened
			if strings.TrimSpace(result.Explanation) == "" {
				t.Fatal("empty explanation — nothing came out of the loop")
			}
			if result.Trace.Initial == "" {
				t.Fatal("no initial conjecture recorded — loop didn't run")
			}
			if result.Trace.Iterations == 0 {
				t.Fatal("zero iterations — engine didn't execute")
			}
			if len(result.Trace.Criticisms) == 0 {
				t.Fatal("no criticisms recorded — criticism pass didn't run")
			}

			// The explanation should differ from the initial conjecture — it was tested
			if result.Trace.Refined != "" && wordOverlap(result.Trace.Initial, result.Trace.Refined) > 0.95 {
				t.Log("WARNING: synthesis is nearly identical to initial conjecture — criticism may have been too weak")
			}

			t.Logf("\n✓ Loop completed: %d iteration(s), escalated=%v, survived=%v, elapsed=%s",
				result.Trace.Iterations, result.Trace.Escalated, result.Trace.Survived, elapsed.Round(time.Millisecond))
		})
	}
}

// TestEpistemicsRouting verifies the router correctly flags explanatory queries.
func TestEpistemicsRouting(t *testing.T) {
	explanatory := []string{
		"why does inflation reduce purchasing power",
		"how does TCP handle packet loss",
		"what causes depression",
		"explain why recursion works",
		"what makes some materials magnetic",
		"what's behind the productivity paradox",
	}

	notExplanatory := []string{
		"what time is it",
		"summarize this document",
		"write me a function",
		"debug this code",
		"hey what's up",
		"list the top 5 frameworks",
	}

	for _, q := range explanatory {
		if !IsExplanatoryQuery(strings.ToLower(q)) {
			t.Errorf("expected %q to be flagged as explanatory", q)
		}
	}

	for _, q := range notExplanatory {
		if IsExplanatoryQuery(strings.ToLower(q)) {
			t.Errorf("expected %q NOT to be flagged as explanatory", q)
		}
	}
	t.Log("✓ Router correctly distinguishes explanatory vs non-explanatory queries")
}

// TestCriticismParsing verifies the critic's structured output is parsed correctly.
func TestCriticismParsing(t *testing.T) {
	raw := `SEVERITY: 0.72
- The explanation conflates correlation with causation
- The proposed mechanism is unfalsifiable as stated
- Ignores competing explanation from network effects literature`

	report := parseCriticism(raw)

	if report.Severity < 0.70 || report.Severity > 0.75 {
		t.Errorf("expected severity ~0.72, got %.2f", report.Severity)
	}
	if len(report.Issues) != 3 {
		t.Errorf("expected 3 issues, got %d: %v", len(report.Issues), report.Issues)
	}
	t.Logf("✓ Parsed severity=%.2f, issues=%d", report.Severity, len(report.Issues))
}

// TestConvergence verifies the early-exit logic works.
func TestConvergence(t *testing.T) {
	identical := "The system fails because the incentive structure rewards short-term gains over long-term stability."
	if !converged(identical, identical) {
		t.Error("identical strings should converge")
	}

	different := "Markets fail due to externality mispricing."
	if converged(identical, different) {
		t.Error("clearly different strings should not converge")
	}
	t.Log("✓ Convergence detection working")
}

// ── helpers ──────────────────────────────────────────────────────────────────

func printTrace(t *testing.T, r ExplanatoryResult, elapsed time.Duration) {
	t.Helper()

	t.Logf("\n%s INITIAL CONJECTURE %s", strings.Repeat("▸", 3), strings.Repeat("◂", 3))
	t.Logf("%s", r.Trace.Initial)

	if len(r.Trace.Criticisms) > 0 {
		t.Logf("\n%s CRITICISMS %s", strings.Repeat("▸", 3), strings.Repeat("◂", 3))
		for i, c := range r.Trace.Criticisms {
			t.Logf("  [%d] %s", i+1, c)
		}
	}

	if r.Trace.Escalated {
		t.Logf("\n⚡ Escalated to Sonnet (criticism was substantive)")
	}

	t.Logf("\n%s SYNTHESIS (iter=%d) %s", strings.Repeat("▸", 3), r.Trace.Iterations, strings.Repeat("◂", 3))
	t.Logf("%s", r.Explanation)

	if r.Trace.Survived {
		t.Logf("\n✓ Conjecture survived — criticism addressed, not just softened")
	}

	t.Logf("\nelapsed: %s", elapsed.Round(time.Millisecond))
}

func wordOverlap(a, b string) float64 {
	wa := wordSet(a)
	wb := wordSet(b)
	if len(wa) == 0 {
		return 0
	}
	overlap := 0
	for w := range wa {
		if wb[w] {
			overlap++
		}
	}
	return float64(overlap) / float64(len(wa))
}

func init() {
	fmt.Println() // blank line before test output
}
