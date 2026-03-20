package cognition

import (
	"fmt"
	"regexp"
	"strings"
)

// --- Pillar 36: NL-to-Symbolic Translation ---
// Ported from Aurora's NLToSymbolicTranslator.swift.
// Translates natural language into formal symbolic formulations.

type TranslationEngine struct {
	StopWords map[string]bool
}

func NewTranslationEngine() *TranslationEngine {
	e := &TranslationEngine{
		StopWords: make(map[string]bool),
	}
	e.loadStopWords()
	return e
}

func (e *TranslationEngine) loadStopWords() {
	words := []string{"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "was"}
	for _, w := range words { e.StopWords[w] = true }
}

// ClassifyProblem categorizes the query into a formal symbolic type.
func (e *TranslationEngine) ClassifyProblem(query string) ProblemType {
	lower := strings.ToLower(query)
	
	if strings.Contains(lower, "schedule") || strings.Contains(lower, "resource") || strings.Contains(lower, "assign") {
		return TypeCSP
	}
	if strings.Contains(lower, "math") || strings.Contains(lower, "calculate") || strings.Contains(lower, "solve for") {
		return TypeSymbolicMath
	}
	if strings.Contains(lower, "if") && strings.Contains(lower, "then") {
		return TypeLogicProg
	}
	if strings.Contains(lower, "true") || strings.Contains(lower, "false") || strings.Contains(lower, "logic puzzle") {
		return TypeSAT
	}
	
	return TypeVerification // Default for deep reasoning
}

// ExtractVariables finds potential unknowns in a symbolic expression.
func (e *TranslationEngine) ExtractVariables(expression string) []string {
	re := regexp.MustCompile(`\b[a-z][a-z0-9]*\b`)
	matches := re.FindAllString(expression, -1)
	
	var variables []string
	seen := make(map[string]bool)
	
	for _, v := range matches {
		if !e.StopWords[v] && len(v) <= 10 && !seen[v] {
			variables = append(variables, v)
			seen[v] = true
		}
	}
	return variables
}

// BuildTranslationPrompt generates instructions for the LLM to perform formal conversion.
func (e *TranslationEngine) BuildTranslationPrompt(query string, pType ProblemType) string {
	return fmt.Sprintf(`Convert the following problem into symbolic expressions:
Problem: %s
Type: %s

Generate expressions in the format:
EXPRESSION_TYPE: expression

Example:
propositional: x AND y
constraint: x + y = 5`, query, pType)
}
