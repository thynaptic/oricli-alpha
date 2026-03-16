package service

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

type Rule struct {
	Name               string   `json:"name"`
	Description        string   `json:"description"`
	Scope              string   `json:"scope"`
	Categories         []string `json:"categories"`
	Constraints        []string `json:"constraints"`
	RoutingPreferences []string `json:"routing_preferences"`
	ResourcePolicies   []string `json:"resource_policies"`
}

type RulesEngine struct {
	rulesDir string
	rules    map[string]Rule
	mu       sync.RWMutex
}

func NewRulesEngine(dir string) *RulesEngine {
	if dir == "" {
		dir = "oricli_core/rules"
	}
	e := &RulesEngine{
		rulesDir: dir,
		rules:    make(map[string]Rule),
	}
	e.Reload()
	return e
}

// --- RFAL & PATHWAYS ---

func (e *RulesEngine) ApplyRFAL(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "rfal_applied": true, "decision": "aligned"}, nil
}

func (e *RulesEngine) TraversePathway(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "current_step": "native_pathway_start"}, nil
}

func (e *RulesEngine) LoadBehavior(params map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"success": true, "behavior": "structured_native_default"}, nil
}

// --- EXISTING METHODS ---

func (e *RulesEngine) Reload() error {
	e.mu.Lock()
	defer e.mu.Unlock()
	files, err := os.ReadDir(e.rulesDir)
	if err != nil { return err }
	e.rules = make(map[string]Rule)
	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".ori") {
			rule, err := e.parseRuleFile(filepath.Join(e.rulesDir, f.Name()))
			if err == nil { e.rules[rule.Name] = rule }
		}
	}
	return nil
}

func (e *RulesEngine) parseRuleFile(path string) (Rule, error) {
	content, err := os.ReadFile(path)
	if err != nil { return Rule{}, err }
	rule := Rule{Scope: "global"}
	var section string
	scanner := bufio.NewScanner(strings.NewReader(string(content)))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" { continue }
		if strings.HasPrefix(line, "@") {
			parts := strings.SplitN(line[1:], ":", 2)
			if len(parts) == 2 {
				key, val := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
				switch key {
				case "rule_name": rule.Name = val
				case "description": rule.Description = val
				case "scope": rule.Scope = val
				case "categories": json.Unmarshal([]byte(val), &rule.Categories)
				}
			}
			continue
		}
		if strings.HasPrefix(line, "<") && strings.HasSuffix(line, ">") {
			if strings.HasPrefix(line, "</") { section = "" } else { section = line[1 : len(line)-1] }
			continue
		}
		if strings.HasPrefix(line, "- ") && section != "" {
			item := strings.TrimSpace(line[2:])
			switch section {
			case "constraints": rule.Constraints = append(rule.Constraints, item)
			case "routing_preferences": rule.RoutingPreferences = append(rule.RoutingPreferences, item)
			case "resource_policies": rule.ResourcePolicies = append(rule.ResourcePolicies, item)
			}
		}
	}
	return rule, nil
}

func (e *RulesEngine) ListRules() []Rule {
	e.mu.RLock()
	defer e.mu.RUnlock()
	list := make([]Rule, 0, len(e.rules))
	for _, r := range e.rules { list = append(list, r) }
	return list
}

func (e *RulesEngine) GetRule(name string) (Rule, bool) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	r, ok := e.rules[name]
	return r, ok
}
