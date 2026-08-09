package forge

import (
	"strconv"
	"strings"
)

// VerifyRequest is the static verification input (no sandbox execution).
type VerifyRequest struct {
	Script      string
	Source      string
	ToolSources []string
	StrictTool  bool // apply full JIT tool contract to Script
}

// VerifyResult is the structured static gate outcome.
type VerifyResult struct {
	OK         bool        `json:"ok"`
	Stage      string      `json:"stage,omitempty"`
	Violations []Violation `json:"violations,omitempty"`
	Summary    string      `json:"summary,omitempty"`
}

// VerifyStatic runs constitution + Go pattern scans. No subprocess, no GOSH exec.
func VerifyStatic(req VerifyRequest) VerifyResult {
	var all []Violation

	if strings.TrimSpace(req.Script) != "" {
		var cons *ScriptConstitution
		if req.StrictTool {
			cons = NewToolConstitution()
		} else {
			cons = NewScriptConstitution()
		}
		v, ok := cons.Check(req.Script)
		all = append(all, v...)
		if !ok {
			return VerifyResult{
				OK:         false,
				Stage:      "script-constitution",
				Violations: all,
				Summary:    cons.Summary(v),
			}
		}
	}

	checkGo := func(label, src string) *VerifyResult {
		v, ok := CheckGoSource(src)
		all = append(all, v...)
		if !ok {
			return &VerifyResult{
				OK:         false,
				Stage:      label,
				Violations: all,
				Summary:    summarize(v),
			}
		}
		return nil
	}

	if strings.TrimSpace(req.Source) != "" {
		if fail := checkGo("go-source", req.Source); fail != nil {
			return *fail
		}
	}
	for i, src := range req.ToolSources {
		if strings.TrimSpace(src) == "" {
			continue
		}
		if fail := checkGo("go-tool", src); fail != nil {
			fail.Stage = "go-tool"
			fail.Summary = "tool[" + strconv.Itoa(i) + "]: " + fail.Summary
			return *fail
		}
	}

	return VerifyResult{
		OK:         true,
		Stage:      "pass",
		Violations: all,
		Summary:    "Constitution: PASS",
	}
}

func summarize(v []Violation) string {
	return NewScriptConstitution().Summary(v)
}
