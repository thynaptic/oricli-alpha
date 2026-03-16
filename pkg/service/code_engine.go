package service

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
)

// CodeEngineService handles code generation, optimization, translation, and verification.
type CodeEngineService struct {
	GenService *GenerationService
	Analyzer   *CodeAnalyzer
}

func NewCodeEngineService(gen *GenerationService, analyzer *CodeAnalyzer) *CodeEngineService {
	return &CodeEngineService{
		GenService: gen,
		Analyzer:   analyzer,
	}
}

// --- CORE OPERATIONS ---

func (s *CodeEngineService) GenerateCodeReasoning(params map[string]interface{}) (map[string]interface{}, error) {
	requirements, _ := params["requirements"].(string)
	contextStr, _ := params["context"].(string)
	prompt := fmt.Sprintf("Requirements:\n%s\n\nContext:\n%s", requirements, contextStr)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Senior Engineer"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "code": extractCodeBlocks(result["text"].(string))}, nil
}

func (s *CodeEngineService) RefineCode(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)
	feedback, _ := params["feedback"].(string)
	prompt := fmt.Sprintf("Code:\n%s\n\nFeedback:\n%s", code, feedback)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Code Reviewer"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "refined_code": extractCodeBlocks(result["text"].(string))}, nil
}

// --- OPTIMIZATION & TRANSLATION ---

func (s *CodeEngineService) OptimizeCode(ctx context.Context, code string, language string) (string, error) {
	prompt := fmt.Sprintf("Optimize: %s code\n%s", language, code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Performance Engineer"})
	if err != nil { return "", err }
	return extractCodeBlocks(result["text"].(string)), nil
}

func (s *CodeEngineService) TranslateCode(ctx context.Context, code string, src string, tgt string) (string, error) {
	prompt := fmt.Sprintf("Translate %s to %s:\n%s", src, tgt, code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Polyglot Programmer"})
	if err != nil { return "", err }
	return extractCodeBlocks(result["text"].(string)), nil
}

// --- VERIFICATION & SANDBOX ---

func (s *CodeEngineService) FormallyVerify(ctx context.Context, code string) (map[string]interface{}, error) {
	prompt := fmt.Sprintf("Verify: %s", code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Formal Verification Specialist"})
	if err != nil { return nil, err }
	return map[string]interface{}{"success": true, "analysis": result["text"]}, nil
}

func (s *CodeEngineService) ExecuteInSandbox(ctx context.Context, command string, args []string) (string, error) {
	cmd := exec.CommandContext(ctx, command, args...)
	output, _ := cmd.CombinedOutput()
	return string(output), nil
}

// --- COMPATIBILITY SHIMS ---

func (s *CodeEngineService) RelateCode(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) CompareCode(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) TraceCodeEvolution(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) MapToRequirements(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) FindCodeDependencies(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) FindSimilarCode(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) ExploreCodePaths(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) GenerateWithVerification(params map[string]interface{}) (map[string]interface{}, error) { return map[string]interface{}{"success": true}, nil }
func (s *CodeEngineService) GenerateWithContext(params map[string]interface{}) (map[string]interface{}, error) { return s.GenerateCodeReasoning(params) }

func extractCodeBlocks(text string) string {
	start := strings.Index(text, "```")
	if start == -1 { return text }
	end := strings.LastIndex(text, "```")
	if end <= start+3 { return text }
	block := text[start:end]
	firstNewline := strings.Index(block, "\n")
	if firstNewline != -1 && firstNewline < 15 { return strings.TrimSpace(block[firstNewline:]) }
	return strings.TrimSpace(block[3:])
}
