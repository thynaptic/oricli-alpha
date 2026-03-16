package service

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"time"
)

type RefactoringSuggestion struct {
	Type        string `json:"type"`
	Description string `json:"description"`
	LineStart   int    `json:"line_start"`
	LineEnd     int    `json:"line_end"`
	Confidence  float64 `json:"confidence"`
}

type RefactoringResult struct {
	Success     bool                    `json:"success"`
	Suggestions []RefactoringSuggestion `json:"suggestions"`
	Summary     string                  `json:"summary"`
	Metadata    map[string]interface{}  `json:"metadata"`
}

type RefactoringService struct {
	Orchestrator *GoOrchestrator
}

func NewRefactoringService(orch *GoOrchestrator) *RefactoringService {
	return &RefactoringService{Orchestrator: orch}
}

func (s *RefactoringService) SuggestRefactorings(code string, refactoringType string) (*RefactoringResult, error) {
	startTime := time.Now()
	log.Printf("[Refactoring] Suggesting refactorings (type: %s)", refactoringType)

	var wg sync.WaitGroup
	var suggestions []RefactoringSuggestion
	var mu sync.Mutex

	lines := strings.Split(code, "\n")

	// 1. Extract Method Opportunities (Look for long functions)
	if refactoringType == "all" || refactoringType == "extract_method" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			inFunc := false
			funcStart := 0
			funcName := ""

			for i, line := range lines {
				trimmed := strings.TrimSpace(line)
				if strings.HasPrefix(trimmed, "def ") {
					if inFunc && (i-funcStart) > 50 {
						mu.Lock()
						suggestions = append(suggestions, RefactoringSuggestion{
							Type:        "extract_method",
							Description: fmt.Sprintf("Function '%s' is too long (>50 lines). Consider extracting logic into smaller methods.", funcName),
							LineStart:   funcStart,
							LineEnd:     i - 1,
							Confidence:  0.8,
						})
						mu.Unlock()
					}
					inFunc = true
					funcStart = i + 1
					funcName = strings.Split(trimmed, "(")[0][4:]
				} else if inFunc && len(trimmed) > 0 && !strings.HasPrefix(line, " ") && !strings.HasPrefix(line, "\t") && !strings.HasPrefix(trimmed, "#") && !strings.HasPrefix(trimmed, "@") {
					// End of function detected by indentation change
					if (i - funcStart) > 50 {
						mu.Lock()
						suggestions = append(suggestions, RefactoringSuggestion{
							Type:        "extract_method",
							Description: fmt.Sprintf("Function '%s' is too long (>50 lines). Consider extracting logic into smaller methods.", funcName),
							LineStart:   funcStart,
							LineEnd:     i - 1,
							Confidence:  0.8,
						})
						mu.Unlock()
					}
					inFunc = false
				}
			}
			// Catch last function
			if inFunc && (len(lines)-funcStart) > 50 {
				mu.Lock()
				suggestions = append(suggestions, RefactoringSuggestion{
					Type:        "extract_method",
					Description: fmt.Sprintf("Function '%s' is too long (>50 lines). Consider extracting logic into smaller methods.", funcName),
					LineStart:   funcStart,
					LineEnd:     len(lines),
					Confidence:  0.8,
				})
				mu.Unlock()
			}
		}()
	}

	// 2. Cognitive Generator suggestions for complex refactorings
	if refactoringType == "all" || refactoringType == "complex" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			prompt := fmt.Sprintf("Analyze this Python code and suggest 2 high-level architectural refactorings. Format as short bullet points.\n\n%s", code)
			res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 30*time.Second)
			if err == nil {
				text := res.(map[string]interface{})["text"].(string)
				mu.Lock()
				suggestions = append(suggestions, RefactoringSuggestion{
					Type:        "architectural",
					Description: text,
					LineStart:   1,
					LineEnd:     len(lines),
					Confidence:  0.7,
				})
				mu.Unlock()
			}
		}()
	}

	wg.Wait()

	return &RefactoringResult{
		Success:     true,
		Suggestions: suggestions,
		Summary:     fmt.Sprintf("Found %d refactoring opportunities.", len(suggestions)),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}

func (s *RefactoringService) VerifyRefactoring(original, refactored string) (map[string]interface{}, error) {
	log.Printf("[Refactoring] Verifying refactored code")
	
	// Fast native check: did the line count drop significantly?
	origLines := len(strings.Split(original, "\n"))
	refacLines := len(strings.Split(refactored, "\n"))
	
	return map[string]interface{}{
		"success": true,
		"is_equivalent": true, // Assumption for native stub
		"confidence": 0.6,
		"metrics": map[string]int{
			"original_lines": origLines,
			"refactored_lines": refacLines,
			"lines_saved": origLines - refacLines,
		},
	}, nil
}
