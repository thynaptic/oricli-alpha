package cognition

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// --- Pillar 35: Sovereign Profile Extensions (.ori) ---
// Implements hot-swappable configuration manifests for personality, rules, and instructions.

type Profile struct {
	Name         string
	Description  string
	Archetype    string
	SassFactor   float64
	Energy       string
	Instructions []string
	Rules        []string
	Skills       []string
}

type ProfileRegistry struct {
	Profiles map[string]*Profile
	Dir      string
	mu       sync.RWMutex
}

func NewProfileRegistry(dir string) *ProfileRegistry {
	r := &ProfileRegistry{
		Profiles: make(map[string]*Profile),
		Dir:      dir,
	}
	r.Reload()
	return r
}

// Reload scans the profiles directory and parses all .ori files.
func (r *ProfileRegistry) Reload() {
	r.mu.Lock()
	defer r.mu.Unlock()

	// Ensure directory exists
	if err := os.MkdirAll(r.Dir, 0755); err != nil {
		log.Printf("[ProfileRegistry] Error creating directory: %v", err)
		return
	}

	files, err := filepath.Glob(filepath.Join(r.Dir, "*.ori"))
	if err != nil {
		log.Printf("[ProfileRegistry] Error scanning directory: %v", err)
		return
	}

	newProfiles := make(map[string]*Profile)
	for _, f := range files {
		profile, err := r.parseProfile(f)
		if err != nil {
			log.Printf("[ProfileRegistry] Error parsing %s: %v", f, err)
			continue
		}
		newProfiles[profile.Name] = profile
		log.Printf("[ProfileRegistry] Loaded profile: %s", profile.Name)
	}

	r.Profiles = newProfiles
}

func (r *ProfileRegistry) GetProfile(name string) (*Profile, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	p, ok := r.Profiles[name]
	return p, ok
}

// parseProfile implements a sectional .ori parser.
func (r *ProfileRegistry) parseProfile(path string) (*Profile, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	p := &Profile{
		Instructions: make([]string, 0),
		Rules:        make([]string, 0),
		Skills:       make([]string, 0),
	}

	scanner := bufio.NewScanner(file)
	var currentSection string

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Parse Tags (@key: value)
		if strings.HasPrefix(line, "@") {
			parts := strings.SplitN(line[1:], ":", 2)
			if len(parts) == 2 {
				key := strings.TrimSpace(parts[0])
				val := strings.TrimSpace(parts[1])
				switch key {
				case "profile_name":
					p.Name = val
				case "description":
					p.Description = val
				case "archetype":
					p.Archetype = val
				case "sass_factor":
					fmt.Sscanf(val, "%f", &p.SassFactor)
				case "energy":
					p.Energy = val
				}
			}
			continue
		}

		// Parse Section Start (<section>)
		if strings.HasPrefix(line, "<") && strings.HasSuffix(line, ">") {
			currentSection = line[1 : len(line)-1]
			continue
		}

		// Parse Section End (</section>)
		if strings.HasPrefix(line, "</") {
			currentSection = ""
			continue
		}

		// Collect items in current section
		if currentSection != "" {
			item := strings.TrimPrefix(line, "- ")
			switch currentSection {
			case "instructions":
				p.Instructions = append(p.Instructions, item)
			case "rules":
				p.Rules = append(p.Rules, item)
			case "skills":
				p.Skills = append(p.Skills, item)
			}
		}
	}

	if p.Name == "" {
		p.Name = strings.TrimSuffix(filepath.Base(path), ".ori")
	}

	return p, nil
}
