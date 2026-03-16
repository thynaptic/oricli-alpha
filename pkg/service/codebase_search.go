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

type SearchMatch struct {
	File      string `json:"file"`
	Line      int    `json:"line"`
	Content   string `json:"content"`
	MatchText string `json:"match_text"`
}

type SearchResult struct {
	Success  bool                   `json:"success"`
	Query    string                 `json:"query"`
	Matches  []SearchMatch          `json:"matches"`
	Summary  string                 `json:"summary"`
	Metadata map[string]interface{} `json:"metadata"`
}

type CodebaseSearchService struct {
	Orchestrator *GoOrchestrator
}

func NewCodebaseSearchService(orch *GoOrchestrator) *CodebaseSearchService {
	return &CodebaseSearchService{Orchestrator: orch}
}

func (s *CodebaseSearchService) SearchCodebase(projectPath string, query string, searchType string) (*SearchResult, error) {
	startTime := time.Now()
	log.Printf("[CodebaseSearch] Searching %s for '%s' (type: %s)", projectPath, query, searchType)

	absPath, err := filepath.Abs(projectPath)
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		return &SearchResult{Success: false}, fmt.Errorf("path does not exist")
	}

	var pythonFiles []string
	err = filepath.Walk(absPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(info.Name(), ".py") {
			pythonFiles = append(pythonFiles, path)
		}
		return nil
	})

	if err != nil {
		return nil, err
	}

	var matches []SearchMatch
	var mu sync.Mutex
	var wg sync.WaitGroup
	
	// Limit concurrency
	sem := make(chan struct{}, 20)

	var re *regexp.Regexp
	if searchType == "regex" {
		re, err = regexp.Compile(query)
		if err != nil {
			return nil, fmt.Errorf("invalid regex: %w", err)
		}
	}

	for _, file := range pythonFiles {
		wg.Add(1)
		go func(f string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			content, err := ioutil.ReadFile(f)
			if err != nil {
				return
			}

			lines := strings.Split(string(content), "\n")
			relPath, _ := filepath.Rel(absPath, f)
			
			localMatches := []SearchMatch{}

			if searchType == "semantic" {
				// Naive fallback for semantic search if we don't hit the orchestrator for every file
				queryLower := strings.ToLower(query)
				for i, line := range lines {
					if strings.Contains(strings.ToLower(line), queryLower) {
						localMatches = append(localMatches, SearchMatch{
							File:      relPath,
							Line:      i + 1,
							Content:   strings.TrimSpace(line),
							MatchText: query,
						})
					}
				}
			} else if searchType == "regex" {
				for i, line := range lines {
					if re.MatchString(line) {
						localMatches = append(localMatches, SearchMatch{
							File:      relPath,
							Line:      i + 1,
							Content:   strings.TrimSpace(line),
							MatchText: re.FindString(line),
						})
					}
				}
			} else {
				// Text search
				for i, line := range lines {
					if strings.Contains(line, query) {
						localMatches = append(localMatches, SearchMatch{
							File:      relPath,
							Line:      i + 1,
							Content:   strings.TrimSpace(line),
							MatchText: query,
						})
					}
				}
			}

			if len(localMatches) > 0 {
				mu.Lock()
				matches = append(matches, localMatches...)
				mu.Unlock()
			}
		}(file)
	}

	wg.Wait()

	return &SearchResult{
		Success: true,
		Query:   query,
		Matches: matches,
		Summary: fmt.Sprintf("Found %d matches across %d files.", len(matches), len(pythonFiles)),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"search_type":    searchType,
			"files_scanned":  len(pythonFiles),
		},
	}, nil
}
