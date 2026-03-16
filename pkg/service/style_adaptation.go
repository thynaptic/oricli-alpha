package service

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

type StyleProfile struct {
	NamingConvention string `json:"naming_convention"`
	Indentation      string `json:"indentation"`
	DocstringStyle   string `json:"docstring_style"`
	QuoteStyle       string `json:"quote_style"`
}

type StyleAdaptationResult struct {
	Success  bool                   `json:"success"`
	Style    *StyleProfile          `json:"style,omitempty"`
	Result   string                 `json:"result,omitempty"`
	Summary  string                 `json:"summary,omitempty"`
	Metadata map[string]interface{} `json:"metadata"`
}

type StyleAdaptationService struct {
	Orchestrator *GoOrchestrator
	StyleCache   map[string]*StyleProfile
	mu           sync.RWMutex
}

func NewStyleAdaptationService(orch *GoOrchestrator) *StyleAdaptationService {
	return &StyleAdaptationService{
		Orchestrator: orch,
		StyleCache:   make(map[string]*StyleProfile),
	}
}

func (s *StyleAdaptationService) DetectStyle(codebase string) (*StyleAdaptationResult, error) {
	startTime := time.Now()
	log.Printf("[StyleAdapt] Detecting style for codebase: %s", codebase)

	absPath, err := filepath.Abs(codebase)
	if err != nil {
		return nil, err
	}

	// Check cache
	s.mu.RLock()
	if cached, ok := s.StyleCache[absPath]; ok {
		s.mu.RUnlock()
		return &StyleAdaptationResult{
			Success: true,
			Style:   cached,
			Summary: "Loaded style from cache.",
			Metadata: map[string]interface{}{
				"execution_time": time.Since(startTime).Seconds(),
				"cached":         true,
			},
		}, nil
	}
	s.mu.RUnlock()

	var pythonFiles []string
	filepath.Walk(absPath, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() && strings.HasSuffix(info.Name(), ".py") {
			pythonFiles = append(pythonFiles, path)
		}
		return nil
	})

	if len(pythonFiles) > 50 {
		pythonFiles = pythonFiles[:50] // Limit sample size
	}

	// Simple heuristic detection
	snakeCaseCount := 0
	camelCaseCount := 0
	spaceIndentCount := 0
	tabIndentCount := 0

	snakeRe := regexp.MustCompile(`def [a-z_][a-z0-9_]*\(`)
	camelRe := regexp.MustCompile(`def [a-z][a-zA-Z0-9]*\(`)

	var wg sync.WaitGroup
	var mu sync.Mutex

	for _, file := range pythonFiles {
		wg.Add(1)
		go func(f string) {
			defer wg.Done()
			content, err := ioutil.ReadFile(f)
			if err != nil {
				return
			}
			text := string(content)

			mu.Lock()
			snakeCaseCount += len(snakeRe.FindAllStringIndex(text, -1))
			camelCaseCount += len(camelRe.FindAllStringIndex(text, -1))
			
			if strings.Contains(text, "\n    ") {
				spaceIndentCount++
			}
			if strings.Contains(text, "\n\t") {
				tabIndentCount++
			}
			mu.Unlock()
		}(file)
	}

	wg.Wait()

	profile := &StyleProfile{
		NamingConvention: "snake_case",
		Indentation:      "4_spaces",
		DocstringStyle:   "google", // Default assumption
		QuoteStyle:       "double",
	}

	if camelCaseCount > snakeCaseCount {
		profile.NamingConvention = "camelCase"
	}
	if tabIndentCount > spaceIndentCount {
		profile.Indentation = "tabs"
	}

	s.mu.Lock()
	s.StyleCache[absPath] = profile
	s.mu.Unlock()

	return &StyleAdaptationResult{
		Success: true,
		Style:   profile,
		Summary: fmt.Sprintf("Detected %s naming and %s indentation.", profile.NamingConvention, profile.Indentation),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"files_scanned":  len(pythonFiles),
		},
	}, nil
}

func (s *StyleAdaptationService) AdaptToStyle(code string, targetStyle map[string]interface{}) (*StyleAdaptationResult, error) {
	startTime := time.Now()
	log.Printf("[StyleAdapt] Adapting code to target style")

	prompt := fmt.Sprintf("Rewrite this Python code to strictly follow this style profile: %v. Only output the rewritten code.\n\n```python\n%s\n```", targetStyle, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("style adaptation failed: %w", err)
	}

	adaptedCode := res.(map[string]interface{})["text"].(string)

	return &StyleAdaptationResult{
		Success: true,
		Result:  adaptedCode,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}
