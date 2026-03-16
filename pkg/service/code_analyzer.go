package service

import (
	"fmt"
	"regexp"
	"strings"
)

type CodeAnalysisResult struct {
	Success      bool                   `json:"success"`
	Functions    int                    `json:"functions"`
	Classes      int                    `json:"classes"`
	Imports      int                    `json:"imports"`
	Loops        int                    `json:"loops"`
	Conditionals int                    `json:"conditionals"`
	Lines        int                    `json:"lines"`
	Characters   int                    `json:"characters"`
	Patterns     []string               `json:"patterns_found"`
}

type CodeAnalyzer struct {
	Patterns map[string]*regexp.Regexp
}

func NewCodeAnalyzer() *CodeAnalyzer {
	return &CodeAnalyzer{
		Patterns: map[string]*regexp.Regexp{
			"function_definition": regexp.MustCompile(`def\s+\w+\s*\(`),
			"class_definition":    regexp.MustCompile(`class\s+\w+`),
			"import_statement":    regexp.MustCompile(`(?m)^(import|from)\s+`),
			"loop":                regexp.MustCompile(`\b(for|while)\s+`),
			"conditional":         regexp.MustCompile(`\b(if|elif|else)\s+`),
			"decorator":           regexp.MustCompile(`@\w+`),
		},
	}
}

func (a *CodeAnalyzer) Analyze(code string) CodeAnalysisResult {
	res := CodeAnalysisResult{
		Success:    true,
		Lines:      len(strings.Split(code, "\n")),
		Characters: len(code),
		Patterns:   make([]string, 0),
	}

	for name, re := range a.Patterns {
		matches := re.FindAllString(code, -1)
		count := len(matches)
		
		switch name {
		case "function_definition":
			res.Functions = count
		case "class_definition":
			res.Classes = count
		case "import_statement":
			res.Imports = count
		case "loop":
			res.Loops = count
		case "conditional":
			res.Conditionals = count
		}

		if count > 0 {
			res.Patterns = append(res.Patterns, name)
		}
	}

	return res
}

func (a *CodeAnalyzer) Explain(code string) string {
	analysis := a.Analyze(code)
	
	var summary []string
	if analysis.Classes > 0 {
		summary = append(summary, fmt.Sprintf("%d classes", analysis.Classes))
	}
	if analysis.Functions > 0 {
		summary = append(summary, fmt.Sprintf("%d functions", analysis.Functions))
	}
	if analysis.Imports > 0 {
		summary = append(summary, fmt.Sprintf("%d imports", analysis.Imports))
	}

	if len(summary) == 0 {
		return "This appears to be a simple script or data file."
	}

	return "Code contains " + strings.Join(summary, ", ") + "."
}
