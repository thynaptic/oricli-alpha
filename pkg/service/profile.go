package service

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"

	"github.com/thynaptic/oricli-go/pkg/core/model"
)

type profileData struct {
	Profiles          []model.AgentProfile `json:"profiles"`
	TaskTypeProfiles  map[string]string    `json:"task_type_profiles"`
	AgentTypeProfiles map[string]string    `json:"agent_type_profiles"`
}

// AgentProfileService handles loading and enforcement of agent profiles in Go
type AgentProfileService struct {
	profiles          map[string]model.AgentProfile
	taskTypeProfiles  map[string]string
	agentTypeProfiles map[string]string
	mu                sync.RWMutex
	configPath        string
	customPath        string
}

func NewAgentProfileService(configPath string) *AgentProfileService {
	s := &AgentProfileService{
		profiles:   make(map[string]model.AgentProfile),
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

	s.profiles = make(map[string]model.AgentProfile)

	// 1. Load built-in profiles
	if err := s.loadFromFile(s.configPath); err != nil {
		return err
	}

	// 2. Load custom profiles if exists
	if _, err := os.Stat(s.customPath); err == nil {
		if err := s.loadFromFile(s.customPath); err != nil {
			log.Printf("[AgentProfile] Warning: failed to load custom profiles: %v", err)
		}
	}

	return nil
}

func (s *AgentProfileService) loadFromFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var pd profileData
	if err := json.Unmarshal(data, &pd); err != nil {
		return err
	}

	for _, p := range pd.Profiles {
		s.profiles[p.Name] = p
	}

	for k, v := range pd.TaskTypeProfiles {
		s.taskTypeProfiles[k] = v
	}

	for k, v := range pd.AgentTypeProfiles {
		s.agentTypeProfiles[k] = v
	}

	return nil
}

func (s *AgentProfileService) GetProfile(name string) (model.AgentProfile, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.profiles[name]
	return p, ok
}

func (s *AgentProfileService) ResolveProfile(profileName, taskType, agentType string) (model.AgentProfile, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if profileName != "" {
		if p, ok := s.profiles[profileName]; ok {
			return p, true
		}
	}

	if taskType != "" {
		if name, ok := s.taskTypeProfiles[taskType]; ok {
			if p, ok := s.profiles[name]; ok {
				return p, true
			}
		}
	}

	if agentType != "" {
		if name, ok := s.agentTypeProfiles[agentType]; ok {
			if p, ok := s.profiles[name]; ok {
				return p, true
			}
		}
	}

	return model.AgentProfile{}, false
}

func (s *AgentProfileService) IsAllowed(p *model.AgentProfile, module, op string) (bool, string) {
	if p == nil {
		return true, ""
	}

	// 1. Blocked Modules
	for _, m := range p.BlockedModules {
		if m == module {
			return false, "module blocked"
		}
	}

	// 2. Blocked Operations
	if ops, ok := p.BlockedOperations[module]; ok {
		for _, blockedOp := range ops {
			if blockedOp == op || blockedOp == "*" {
				return false, "operation blocked"
			}
		}
	}

	// 3. Allowed Modules (if specified, acts as allowlist)
	if len(p.AllowedModules) > 0 {
		allowed := false
		for _, m := range p.AllowedModules {
			if m == module {
				allowed = true
				break
			}
		}
		if !allowed {
			return false, "module not in allowlist"
		}
	}

	return true, ""
}

func (s *AgentProfileService) ListProfiles() []model.AgentProfile {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]model.AgentProfile, 0, len(s.profiles))
	for _, p := range s.profiles {
		out = append(out, p)
	}
	return out
}

func (s *AgentProfileService) AddProfile(p model.AgentProfile) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.profiles[p.Name] = p
	return nil
}

func (s *AgentProfileService) UpdateProfile(p model.AgentProfile) error {
	return s.AddProfile(p)
}

func (s *AgentProfileService) DeleteProfile(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.profiles, name)
	return nil
}
