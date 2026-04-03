// Package precompute detects questions that require exact factual computation
// (arithmetic, keyboard mappings, unit conversions) and injects the pre-computed
// answer directly into the composite before generation.
//
// Philosophy: LLMs are bad at large arithmetic and symbol-mapping tasks. Instead
// of asking the model to compute, we compute in Go and hand it the answer. This
// is separate from trapcheck (which guides reasoning about trick questions) —
// precompute provides hard facts, not reasoning hints.
package precompute

import (
	"fmt"
	"math/big"
	"regexp"
	"strings"
)

// Result holds a precomputed answer to inject.
type Result struct {
	Label  string // human label for the computation performed
	Answer string // exact answer to inject
}

// reArith matches a simple binary arithmetic expression: number OP number.
// Supports +, -, *, /, × (unicode multiply).
var reArith = regexp.MustCompile(
	`([\d,_]+)\s*([+\-*/×÷])\s*([\d,_]+)`,
)

// reSpelledBackwards matches "what is 'word' spelled backwards" style questions.
var reSpelledBackwards = regexp.MustCompile(
	`(?i)(?:what\s+is\s+)?['"` + "`" + `]?([A-Za-z]{3,})['"` + "`" + `]?\s+spelled\s+backwards`,
)

// reNotWord matches standalone "not" tokens.
var reNotWord = regexp.MustCompile(`(?i)\bnot\b`)

// reQWERTY matches QWERTY keyboard shift questions.
// Looks for the example form "X goes to Y" and "what does Z" / "Z go to".
var reQWERTYExample = regexp.MustCompile(
	`(?i)([A-Z]{3,})\s+goes\s+to\s+([A-Z]{3,})`,
)
var reQWERTYTarget = regexp.MustCompile(
	`(?i)what\s+does\s+([A-Z]{3,})\s+(?:go\s+to|become|map\s+to)`,
)

// QWERTY linear key sequence — ordered left-to-right, row by row.
// This is the sequence used to define "shift right by 1".
const qwertySeq = "QWERTYUIOPASDFGHJKL;ZXCVBNM"

// shiftQWERTY shifts each letter in word right by n positions in qwertySeq.
// Letters not found in the sequence are passed through unchanged.
func shiftQWERTY(word string, n int) string {
	seq := []rune(qwertySeq)
	pos := make(map[rune]int, len(seq))
	for i, r := range seq {
		pos[r] = i
	}
	var sb strings.Builder
	for _, r := range strings.ToUpper(word) {
		if idx, ok := pos[r]; ok {
			newIdx := idx + n
			if newIdx >= 0 && newIdx < len(seq) {
				sb.WriteRune(seq[newIdx])
			} else {
				sb.WriteRune('?') // out of bounds (e.g., shifting P right)
			}
		} else {
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

// evalArith evaluates a simple binary arithmetic expression using math/big
// for exact integer arithmetic (handles 64-bit overflow correctly).
// Returns (result string, ok bool).
func evalArith(left, op, right string) (string, bool) {
	// Strip formatting separators
	cleanNum := func(s string) string {
		return strings.NewReplacer(",", "", "_", "").Replace(s)
	}
	a := new(big.Int)
	b := new(big.Int)
	if _, ok := a.SetString(cleanNum(left), 10); !ok {
		return "", false
	}
	if _, ok := b.SetString(cleanNum(right), 10); !ok {
		return "", false
	}
	result := new(big.Int)
	switch op {
	case "+":
		result.Add(a, b)
	case "-":
		result.Sub(a, b)
	case "*", "×":
		result.Mul(a, b)
	case "/", "÷":
		if b.Sign() == 0 {
			return "undefined (division by zero)", true
		}
		result.Quo(a, b)
	default:
		return "", false
	}
	return result.String(), true
}

// Compute scans the stimulus for computable patterns and returns zero or more
// Results. Returns empty slice for queries with no computable content.
func Compute(stimulus string) []Result {
	var results []Result
	s := stimulus

	// ── Backwards spelling ────────────────────────────────────────────────────
	if m := reSpelledBackwards.FindStringSubmatch(s); m != nil {
		word := m[1]
		runes := []rune(strings.ToLower(word))
		for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
			runes[i], runes[j] = runes[j], runes[i]
		}
		reversed := string(runes)
		results = append(results, Result{
			Label:  "backwards spelling",
			Answer: fmt.Sprintf("'%s' spelled backwards is '%s'", strings.ToLower(word), reversed),
		})
	}

	// ── Negation chain counting ───────────────────────────────────────────────
	// Only fires for 2+ "not" tokens — clear signal of a negation-chain test.
	// Counts exactly, derives polarity, and injects the definitive Yes/No.
	if notMatches := reNotWord.FindAllString(s, -1); len(notMatches) >= 2 {
		n := len(notMatches)
		polarity := "NEGATIVE"
		answer := "No"
		parity := "odd"
		if n%2 == 0 {
			polarity = "POSITIVE"
			answer = "Yes"
			parity = "even"
		}
		results = append(results, Result{
			Label: "negation chain",
			Answer: fmt.Sprintf(
				"Counted %d 'not' words (%s number). %d negations = %s statement. Direct answer: %s",
				n, parity, n, polarity, answer,
			),
		})
	}

	// ── Arithmetic ────────────────────────────────────────────────────────────
	if m := reArith.FindStringSubmatch(s); m != nil {
		if val, ok := evalArith(m[1], m[2], m[3]); ok {
			opLabel := map[string]string{
				"+": "addition", "-": "subtraction",
				"*": "multiplication", "×": "multiplication",
				"/": "division", "÷": "division",
			}[m[2]]
			results = append(results, Result{
				Label:  fmt.Sprintf("arithmetic (%s)", opLabel),
				Answer: fmt.Sprintf("%s %s %s = %s", m[1], m[2], m[3], val),
			})
		}
	}

	// ── QWERTY keyboard shift ─────────────────────────────────────────────────
	exMatch := reQWERTYExample.FindStringSubmatch(s)
	tgtMatch := reQWERTYTarget.FindStringSubmatch(s)
	if exMatch != nil && tgtMatch != nil {
		example := exMatch[1]
		exResult := exMatch[2]
		target := tgtMatch[1]

		// Infer shift distance from the given example pair.
		// Try shifts -5..+5 and find the one that matches the example.
		inferredShift := 0
		found := false
		for n := -5; n <= 5; n++ {
			if n == 0 {
				continue
			}
			if shiftQWERTY(example, n) == strings.ToUpper(exResult) {
				inferredShift = n
				found = true
				break
			}
		}
		if found {
			answer := shiftQWERTY(target, inferredShift)
			dir := "right"
			if inferredShift < 0 {
				dir = "left"
			}
			results = append(results, Result{
				Label: fmt.Sprintf("QWERTY shift %+d (%s)", inferredShift, dir),
				Answer: fmt.Sprintf(
					"Applying the same QWERTY shift that maps %s→%s (shift %+d %s): %s → %s",
					example, exResult, inferredShift, dir, target, answer,
				),
			})
		}
	}

	return results
}

// FormatInjection builds the injection block from precomputed results.
// Returns empty string when no results (no-op for normal queries).
func FormatInjection(results []Result) string {
	if len(results) == 0 {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("### PRECALCULATED FACTS\n")
	sb.WriteString("The following values have been computed exactly. Use them directly — do NOT recompute.\n")
	for _, r := range results {
		sb.WriteString(fmt.Sprintf("• [%s] %s\n", r.Label, r.Answer))
	}
	sb.WriteString("### END PRECALCULATED FACTS\n")
	return sb.String()
}
