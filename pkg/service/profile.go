package service

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// AgentProfile represents a declarative policy for a task-specific agent
type AgentProfile struct {
	Name               string              `json:"name"`
	Description        string              `json:"description"`
	AllowedModules     []string            `json:"allowed_modules"`
	AllowedOperations  map[string][]string `json:"allowed_operations"`
	BlockedModules     []string            `json:"blocked_modules"`
	BlockedOperations  map[string][]string `json:"blocked_operations"`
	SystemInstructions string              `json:"system_instructions"`
	ModelPreference    string              `json:"model_preference"`
	TaskTags           []string            `json:"task_tags"`
	SkillOverlays      []string            `json:"skill_overlays"`
}

type profileData struct {
	Profiles          []AgentProfile    `json:"profiles"`
	TaskTypeProfiles  map[string]string `json:"task_type_profiles"`
	AgentTypeProfiles map[string]string `json:"agent_type_profiles"`
}

// AgentProfileService handles loading and enforcement of agent profiles in Go
type AgentProfileService struct {
	profiles          map[string]AgentProfile
	taskTypeProfiles  map[string]string
	agentTypeProfiles map[string]string
	mu                sync.RWMutex
	configPath        string
	customPath        string
}

func NewAgentProfileService(configPath string) *AgentProfileService {
	s := &AgentProfileService{
		profiles:   make(map[string]AgentProfile),
		configPath: configPath,
		customPath: filepath.Join(filepath.Dir(configPath), "custom_profiles.json"),
	}
	s.Reload()
	return s
}

// Reload loads profiles from disk
func (s *AgentProfileService) Reload() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.profiles = make(map[string]AgentProfile)

	// 1. Load built-in profiles
	if err := s.loadFromFile(s.configPath); err != nil {
		return err
	}

	// 2. Load custom profiles (overriding built-ins)
	if _, err := os.Stat(s.customPath); err == nil {
		s.loadFromFile(s.customPath)
	}

	return nil
}

func (s *AgentProfileService) loadFromFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("failed to read profile file: %w", err)
	}

	var pd profileData
	if err := json.Unmarshal(data, &pd); err != nil {
		return fmt.Errorf("failed to unmarshal profiles: %w", err)
	}

	for _, p := range pd.Profiles {
		s.profiles[p.Name] = p
	}

	if pd.TaskTypeProfiles != nil {
		s.taskTypeProfiles = pd.TaskTypeProfiles
	}
	if pd.AgentTypeProfiles != nil {
		s.agentTypeProfiles = pd.AgentTypeProfiles
	}

	return nil
}

// GetProfile returns a profile by name
func (s *AgentProfileService) GetProfile(name string) (AgentProfile, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.profiles[name]
	return p, ok
}

// ResolveProfile finds a profile by name, task type, or agent type
func (s *AgentProfileService) ResolveProfile(profileName, taskType, agentType string) (AgentProfile, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	name := profileName
	if name == "" && taskType != "" {
		name = s.taskTypeProfiles[taskType]
	}
	if name == "" && agentType != "" {
		name = s.agentTypeProfiles[agentType]
	}

	if name == "" {
		return AgentProfile{}, false
	}

	p, ok := s.profiles[name]
	return p, ok
}

// ListProfiles returns all loaded profiles
func (s *AgentProfileService) ListProfiles() []AgentProfile {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	list := make([]AgentProfile, 0, len(s.profiles))
	for _, p := range s.profiles {
		list = append(list, p)
	}
	return list
}

// IsAllowed enforces the profile policy for a given module and operation
func (s *AgentProfileService) IsAllowed(profile *AgentProfile, moduleName, operation string) (bool, string) {
	if profile == nil {
		return true, ""
	}

	// Check blocked modules
	for _, m := range profile.BlockedModules {
		if m == moduleName {
			return false, fmt.Sprintf("Module '%s' is blocked by profile '%s'", moduleName, profile.Name)
		}
	}

	// Check blocked operations
	if blockedOps, ok := profile.BlockedOperations[moduleName]; ok {
		for _, op := range blockedOps {
			if op == operation || op == "*" {
				return false, fmt.Sprintf("Operation '%s' on module '%s' is blocked by profile '%s'", operation, moduleName, profile.Name)
			}
		}
	}

	// Check allowed modules (whitelist)
	if len(profile.AllowedModules) > 0 {
		allowed := false
		for _, m := range profile.AllowedModules {
			if m == moduleName {
				allowed = true
				break
			}
		}
		if !allowed {
			return false, fmt.Sprintf("Module '%s' is not in the allowed list for profile '%s'", moduleName, profile.Name)
		}
	}

	// Check allowed operations (whitelist)
	if allowedOps, ok := profile.AllowedOperations[moduleName]; ok {
		allowed := false
		for _, op := range allowedOps {
			if op == operation {
				allowed = true
				break
			}
		}
		if !allowed {
			return false, fmt.Sprintf("Operation '%s' on module '%s' is not in the allowed list for profile '%s'", operation, moduleName, profile.Name)
		}
	}

	return true, ""
}
