package forge

import (
	"fmt"
	"regexp"
	"strings"
)

// Go forbidden patterns — reform Stage 1 only (no gofmt/vet/build).
var goForbiddenPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)//\s*(TODO|FIXME|HACK|XXX|PLACEHOLDER|STUB|NOT IMPLEMENTED)`),
	regexp.MustCompile(`panic\("not implemented"\)`),
	regexp.MustCompile(`panic\("TODO`),
	regexp.MustCompile(`(?m)\bfunc\b[^{]+\{\s*\}`),
	regexp.MustCompile(`(?m)^\s*_\s*=\s*\S+\s*$`),
}

// Capsule Yaegi tool perimeter — block obvious escape hatches (static).
var goEscapePatterns = []*regexp.Regexp{
	regexp.MustCompile(`\bos/exec\b`),
	regexp.MustCompile(`\bnet/http\b`),
	regexp.MustCompile(`\bsyscall\b`),
	regexp.MustCompile(`\bunsafe\b`),
	regexp.MustCompile(`\bioutil\.ReadFile\b|\bos\.ReadFile\s*\(\s*"/`),
}

// CheckGoSource scans Yaegi Go source for stubs and escape hatches.
func CheckGoSource(source string) ([]Violation, bool) {
	if strings.TrimSpace(source) == "" {
		return nil, true
	}
	var violations []Violation
	for _, pat := range goForbiddenPatterns {
		if loc := pat.FindStringIndex(source); loc != nil {
			end := loc[1] + 40
			if end > len(source) {
				end = len(source)
			}
			violations = append(violations, Violation{
				Rule:   "go_forbidden_pattern",
				Detail: fmt.Sprintf("near: %q", strings.TrimSpace(source[loc[0]:end])),
				Fatal:  true,
			})
		}
	}
	for _, pat := range goEscapePatterns {
		if loc := pat.FindStringIndex(source); loc != nil {
			end := loc[1] + 40
			if end > len(source) {
				end = len(source)
			}
			violations = append(violations, Violation{
				Rule:   "go_escape_hatch",
				Detail: fmt.Sprintf("near: %q", strings.TrimSpace(source[loc[0]:end])),
				Fatal:  true,
			})
		}
	}
	return violations, len(violations) == 0
}
