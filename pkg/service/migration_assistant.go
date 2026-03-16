package service

import (
	"fmt"
	"log"
	"time"
)

type MigrationResult struct {
	Success  bool                   `json:"success"`
	Result   string                 `json:"result,omitempty"`
	Plan     map[string]interface{} `json:"plan,omitempty"`
	Metadata map[string]interface{} `json:"metadata"`
}

type MigrationAssistantService struct {
	Orchestrator *GoOrchestrator
}

func NewMigrationAssistantService(orch *GoOrchestrator) *MigrationAssistantService {
	return &MigrationAssistantService{Orchestrator: orch}
}

func (s *MigrationAssistantService) PlanMigration(code string, targetVersion string) (*MigrationResult, error) {
	startTime := time.Now()
	log.Printf("[Migration] Planning migration to Python %s", targetVersion)

	prompt := fmt.Sprintf("Analyze this Python code and create a detailed migration plan to upgrade it to Python %s. Format the response as JSON with keys 'issues_found', 'migration_steps', and 'breaking_changes'.\n\n```python\n%s\n```", targetVersion, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("migration planning failed: %w", err)
	}

	planText := res.(map[string]interface{})["text"].(string)

	return &MigrationResult{
		Success: true,
		Plan: map[string]interface{}{
			"target_version": targetVersion,
			"details":        planText,
		},
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}

func (s *MigrationAssistantService) MigratePythonVersion(code string, fromVersion string, toVersion string) (*MigrationResult, error) {
	startTime := time.Now()
	log.Printf("[Migration] Migrating code from Python %s to %s", fromVersion, toVersion)

	prompt := fmt.Sprintf("Rewrite this Python %s code to be idiomatic Python %s. Only output the new code.\n\n```python\n%s\n```", fromVersion, toVersion, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 90*time.Second)
	if err != nil {
		return nil, fmt.Errorf("migration generation failed: %w", err)
	}

	migratedCode := res.(map[string]interface{})["text"].(string)

	return &MigrationResult{
		Success: true,
		Result:  migratedCode,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"from_version":   fromVersion,
			"to_version":     toVersion,
		},
	}, nil
}

func (s *MigrationAssistantService) MigrateLibrary(code string, oldLib string, newLib string) (*MigrationResult, error) {
	startTime := time.Now()
	log.Printf("[Migration] Migrating library from %s to %s", oldLib, newLib)

	prompt := fmt.Sprintf("Rewrite this Python code to replace the '%s' library with the '%s' library. Only output the new code.\n\n```python\n%s\n```", oldLib, newLib, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 90*time.Second)
	if err != nil {
		return nil, fmt.Errorf("library migration failed: %w", err)
	}

	migratedCode := res.(map[string]interface{})["text"].(string)

	return &MigrationResult{
		Success: true,
		Result:  migratedCode,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"old_lib":        oldLib,
			"new_lib":        newLib,
		},
	}, nil
}
