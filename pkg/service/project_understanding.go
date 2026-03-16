package service

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type ProjectModule struct {
	File      string   `json:"file"`
	Name      string   `json:"name"`
	Classes   []string `json:"classes"`
	Functions []string `json:"functions"`
}

type ProjectInfo struct {
	TotalFiles  int             `json:"total_files"`
	TotalLines  int             `json:"total_lines"`
	Modules     []ProjectModule `json:"modules"`
	Packages    []string        `json:"packages"`
	EntryPoints []string        `json:"entry_points"`
}

type ProjectUnderstandingResult struct {
	Success     bool                   `json:"success"`
	ProjectInfo ProjectInfo            `json:"project_info"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type ProjectUnderstandingService struct {
	Orchestrator *GoOrchestrator
}

func NewProjectUnderstandingService(orch *GoOrchestrator) *ProjectUnderstandingService {
	return &ProjectUnderstandingService{Orchestrator: orch}
}

func (s *ProjectUnderstandingService) UnderstandProject(projectPath string) (*ProjectUnderstandingResult, error) {
	startTime := time.Now()
	log.Printf("[ProjectUnder] Understanding project at: %s", projectPath)

	absPath, err := filepath.Abs(projectPath)
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		return &ProjectUnderstandingResult{Success: false}, fmt.Errorf("path does not exist")
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

	info := ProjectInfo{
		TotalFiles: len(pythonFiles),
	}

	var mu sync.Mutex
	var wg sync.WaitGroup
	
	// Limit concurrency to avoid too many open files
	sem := make(chan struct{}, 20)

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

			lines := len(strings.Split(string(content), "\n"))
			relPath, _ := filepath.Rel(absPath, f)
			
			// Minimal parsing for now (could use a Python sidecar or Go-native parser later)
			modName := strings.ReplaceAll(strings.TrimSuffix(relPath, ".py"), "/", ".")
			
			mu.Lock()
			info.TotalLines += lines
			info.Modules = append(info.Modules, ProjectModule{
				File: relPath,
				Name: modName,
			})
			mu.Unlock()
		}(file)
	}

	wg.Wait()

	return &ProjectUnderstandingResult{
		Success:     true,
		ProjectInfo: info,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"project_path":   absPath,
		},
	}, nil
}
