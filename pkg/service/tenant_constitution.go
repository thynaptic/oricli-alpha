package service

import (
	"bufio"
	"log"
	"os"
	"strings"
	"sync"
)

const maxTenantInjectChars = 600

// TenantConstitution is the SMB/operator behavioral layer.
// It is loaded once at startup from a .ori file and injected into every system
// prompt ABOVE the LivingConstitution — but BELOW the compiled core rules which
// are always re-asserted afterward. SMBs can ADD identity, rules, and banned
// topics; they cannot remove or override Oricli's sovereign core.
//
// Satisfies cognition.ConstitutionProvider.
type TenantConstitution struct {
	Name           string   // @name
	Persona        string   // @persona  (optional custom name for this deployment)
	Company        string   // @company
	IdentityOverride string // <identity_override> block
	Rules          []string // <rules> block
	BannedTopics   []string // <banned_topics> block
	mu             sync.RWMutex
}

// LoadTenantConstitution reads a .ori constitution file from path and returns a
// populated TenantConstitution. Returns nil (not an error) when path is empty so
// callers can treat a missing path as "no tenant layer".
func LoadTenantConstitution(path string) *TenantConstitution {
	if path == "" {
		return nil
	}

	tc := &TenantConstitution{}
	if err := tc.load(path); err != nil {
		log.Printf("[TenantConstitution] Failed to load %q: %v — tenant layer disabled", path, err)
		return nil
	}
	log.Printf("[TenantConstitution] Loaded constitution for %q (%d rules, %d bans)",
		tc.Company, len(tc.Rules), len(tc.BannedTopics))
	return tc
}

// HasRules satisfies cognition.ConstitutionProvider.
func (tc *TenantConstitution) HasRules() bool {
	if tc == nil {
		return false
	}
	tc.mu.RLock()
	defer tc.mu.RUnlock()
	return len(tc.Rules) > 0 || tc.IdentityOverride != "" || len(tc.BannedTopics) > 0
}

// Inject satisfies cognition.ConstitutionProvider. Returns the tenant layer as a
// compact system-prompt block. Always stays under maxTenantInjectChars.
func (tc *TenantConstitution) Inject() string {
	if tc == nil {
		return ""
	}
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	var sb strings.Builder

	// Identity override — replaces the "presented as" persona, not the core sovereignty
	if tc.IdentityOverride != "" {
		sb.WriteString("### DEPLOYMENT IDENTITY:\n")
		sb.WriteString(strings.TrimSpace(tc.IdentityOverride))
		sb.WriteString("\n\n")
	}

	// Operator rules — additive constraints on top of core
	if len(tc.Rules) > 0 {
		sb.WriteString("### OPERATOR RULES (non-negotiable for this deployment):\n")
		for _, r := range tc.Rules {
			line := "- " + r + "\n"
			if sb.Len()+len(line) > maxTenantInjectChars-50 {
				break
			}
			sb.WriteString(line)
		}
		sb.WriteString("\n")
	}

	// Banned topics — hard stops
	if len(tc.BannedTopics) > 0 {
		sb.WriteString("### BANNED TOPICS (decline gracefully, do not engage):\n")
		for _, t := range tc.BannedTopics {
			line := "- " + t + "\n"
			if sb.Len()+len(line) > maxTenantInjectChars {
				break
			}
			sb.WriteString(line)
		}
	}

	result := strings.TrimRight(sb.String(), "\n")
	if len(result) > maxTenantInjectChars {
		result = result[:maxTenantInjectChars]
	}
	return result
}

// load parses the .ori file format into the TenantConstitution fields.
//
// Supported directives:
//
//	@name:    display name
//	@persona: custom assistant name for this deployment
//	@company: company name
//
// Supported blocks:
//
//	<identity_override> ... </identity_override>
//	<rules> ... </rules>
//	<banned_topics> ... </banned_topics>
func (tc *TenantConstitution) load(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	tc.mu.Lock()
	defer tc.mu.Unlock()

	type block int
	const (
		blockNone block = iota
		blockIdentity
		blockRules
		blockBanned
	)

	var current block
	var identityLines []string

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		trimmed := strings.TrimSpace(line)

		// Skip blank lines and comments outside blocks
		if trimmed == "" || (strings.HasPrefix(trimmed, "#") && current == blockNone) {
			continue
		}

		// Block open tags
		switch trimmed {
		case "<identity_override>":
			current = blockIdentity
			continue
		case "<rules>":
			current = blockRules
			continue
		case "<banned_topics>":
			current = blockBanned
			continue
		}

		// Block close tags
		if strings.HasPrefix(trimmed, "</") {
			if current == blockIdentity {
				tc.IdentityOverride = strings.Join(identityLines, "\n")
			}
			current = blockNone
			continue
		}

		// Inside blocks
		switch current {
		case blockIdentity:
			identityLines = append(identityLines, line)
		case blockRules:
			if entry := parseListEntry(trimmed); entry != "" {
				tc.Rules = append(tc.Rules, entry)
			}
		case blockBanned:
			if entry := parseListEntry(trimmed); entry != "" {
				tc.BannedTopics = append(tc.BannedTopics, entry)
			}
		case blockNone:
			// Directive lines: @key: value
			if strings.HasPrefix(trimmed, "@") {
				parts := strings.SplitN(trimmed[1:], ":", 2)
				if len(parts) == 2 {
					key := strings.TrimSpace(parts[0])
					val := strings.TrimSpace(parts[1])
					switch key {
					case "name":
						tc.Name = val
					case "persona":
						tc.Persona = val
					case "company":
						tc.Company = val
					}
				}
			}
		}
	}

	return scanner.Err()
}

// parseListEntry strips leading "- " or "* " bullets from a list line.
func parseListEntry(s string) string {
	s = strings.TrimSpace(s)
	if s == "" || strings.HasPrefix(s, "#") {
		return ""
	}
	for _, prefix := range []string{"- ", "* ", "• "} {
		if strings.HasPrefix(s, prefix) {
			return strings.TrimSpace(s[len(prefix):])
		}
	}
	return s
}
