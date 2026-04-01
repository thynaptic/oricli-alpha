package service

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

type AgentSkill struct {
	Name          string   `json:"skill_name"`
	Description   string   `json:"description"`
	Triggers      []string `json:"triggers"`
	RequiresTools []string `json:"requires_tools"`
	Mindset       string   `json:"mindset"`
	Instructions  string   `json:"instructions"`
	Constraints   string   `json:"constraints"`
}

type SkillManager struct {
	skillsDir string
	skills    map[string]AgentSkill
	mu       sync.RWMutex
}

func NewSkillManager(dir string) *SkillManager {
	if dir == "" { dir = "oricli_core/rules" } // Corrected to match rules engine root if needed
	sm := &SkillManager{skillsDir: dir, skills: make(map[string]AgentSkill)}
	sm.Reload()
	return sm
}

// --- SKILL & SERVICE DISCOVERY ---

func (sm *SkillManager) RegisterSkill(s AgentSkill) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	sm.skills[s.Name] = s
}

func (sm *SkillManager) DiscoverServices(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "services": []string{"backbone", "worker", "ollama"}}, nil
}

// --- EXISTING METHODS ---

func (sm *SkillManager) Reload() error {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	files, err := os.ReadDir(sm.skillsDir)
	if err != nil { return err }
	sm.skills = make(map[string]AgentSkill)
	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".ori") {
			skill, err := sm.parseSkillFile(filepath.Join(sm.skillsDir, f.Name()))
			if err == nil { sm.skills[skill.Name] = skill }
		}
	}
	return nil
}

func (sm *SkillManager) parseSkillFile(path string) (AgentSkill, error) {
	content, err := os.ReadFile(path)
	if err != nil { return AgentSkill{}, err }
	skill := AgentSkill{}
	contentStr := string(content)
	scanner := bufio.NewScanner(strings.NewReader(contentStr))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "@") {
			parts := strings.SplitN(line[1:], ":", 2)
			if len(parts) == 2 {
				key, val := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
				switch key {
				case "skill_name": skill.Name = val
				case "description": skill.Description = val
				case "triggers": json.Unmarshal([]byte(val), &skill.Triggers)
				case "requires_tools": json.Unmarshal([]byte(val), &skill.RequiresTools)
				}
			}
		}
	}
	mr := regexp.MustCompile(`(?s)<mindset>(.*?)</mindset>`)
	if m := mr.FindStringSubmatch(contentStr); len(m) > 1 { skill.Mindset = strings.TrimSpace(m[1]) }
	ir := regexp.MustCompile(`(?s)<instructions>(.*?)</instructions>`)
	if m := ir.FindStringSubmatch(contentStr); len(m) > 1 { skill.Instructions = strings.TrimSpace(m[1]) }
	cr := regexp.MustCompile(`(?s)<constraints>(.*?)</constraints>`)
	if m := cr.FindStringSubmatch(contentStr); len(m) > 1 { skill.Constraints = strings.TrimSpace(m[1]) }
	return skill, nil
}

func (sm *SkillManager) ListSkills() []AgentSkill {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	list := make([]AgentSkill, 0, len(sm.skills))
	for _, s := range sm.skills { list = append(list, s) }
	return list
}

func (sm *SkillManager) GetSkill(name string) (AgentSkill, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	s, ok := sm.skills[name]
	return s, ok
}

func (sm *SkillManager) MatchSkills(query string) []AgentSkill {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	ql := strings.ToLower(query)
	var matches []AgentSkill
	for _, s := range sm.skills {
		for _, t := range s.Triggers {
			if strings.Contains(ql, strings.ToLower(t)) { matches = append(matches, s); break }
		}
	}
	return matches
}

// ---------------------------------------------------------------------------
// P5-3: Peer SkillManifest cache (ESI — Epistemic Skill Inheritance)
// ---------------------------------------------------------------------------

// peerManifestKey returns the cache key for a peer manifest.
func peerManifestKey(skill, nodeShortID string) string {
return "peer:" + nodeShortID + ":" + skill
}

// CachePeerManifest stores a peer-broadcasted .ori skill addendum (system-prompt section)
// in memory so it can be loaded via X-ORI-Manifest: peer:<skill> header dispatch.
func (sm *SkillManager) CachePeerManifest(skill, nodeShortID, systemAddendum string) {
sm.mu.Lock()
defer sm.mu.Unlock()
sm.skills[peerManifestKey(skill, nodeShortID)] = AgentSkill{
Name:        peerManifestKey(skill, nodeShortID),
Description: "Peer manifest from " + nodeShortID,
Triggers:    []string{skill},
Instructions: systemAddendum,
}
}

// GetPeerManifest retrieves a cached peer manifest for the given skill.
// Returns the system addendum and whether it was found.
func (sm *SkillManager) GetPeerManifest(skill, nodeShortID string) (string, bool) {
sm.mu.RLock()
defer sm.mu.RUnlock()
s, ok := sm.skills[peerManifestKey(skill, nodeShortID)]
if !ok {
return "", false
}
return s.Instructions, true
}
