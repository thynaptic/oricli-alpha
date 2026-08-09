package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	Port            int
	CapsuleKey      string
	DefaultProvider string
	OpenCodeBaseURL string
	MemoryDir       string
	MemoryKey       string // base64 32-byte AES key; empty → derived from MemoryDir (dev)
	MaxSessionTurns int

	// GOSH — docker-friendly shell sandbox
	GoshEnabled     bool
	GoshWorkspace   string // container path, e.g. /workspace (overlay); empty → mem-only
	GoshForceMem    bool
	GoshExecTimeout time.Duration

	// Skills — read-only .ori overlays (colon-separated dirs)
	SkillsDirs []string
	// Agents — read-only .agent.md profiles
	AgentsDirs []string

	// Light JIT forge (in-memory only)
	ForgeMaxTools int
	ForgeTTL      time.Duration

	// CORS — empty disables; "*" or comma-separated origins
	CORSOrigins []string
}

func Load() Config {
	port := 8089
	if v := os.Getenv("ORI_CAPSULE_PORT"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			port = n
		}
	}
	defProv := os.Getenv("ORI_DEFAULT_PROVIDER")
	if defProv == "" {
		defProv = "openai"
	}
	ocBase := os.Getenv("ORI_OPENCODE_BASE_URL")
	if ocBase == "" {
		ocBase = "https://opencode.ai/zen/v1"
	}
	memDir := os.Getenv("ORI_MEMORY_DIR")
	if memDir == "" {
		memDir = ".memory"
	}
	maxTurns := 24
	if v := os.Getenv("ORI_MEMORY_MAX_TURNS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxTurns = n
		}
	}

	goshEnabled := true
	if v := os.Getenv("ORI_GOSH_ENABLED"); v != "" {
		goshEnabled = v == "1" || v == "true" || v == "yes"
	}
	goshWS := os.Getenv("ORI_GOSH_WORKSPACE")
	goshForceMem := os.Getenv("ORI_GOSH_FORCE_MEM") == "1" || os.Getenv("ORI_GOSH_FORCE_MEM") == "true"
	goshTimeout := 5 * time.Second
	if v := os.Getenv("ORI_GOSH_TIMEOUT_SEC"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			goshTimeout = time.Duration(n) * time.Second
		}
	}

	skillsDirs := splitDirs(os.Getenv("ORI_SKILLS_DIR"))
	if len(skillsDirs) == 0 {
		// Dev-friendly default when running from monorepo root or ori-capsule/.
		for _, cand := range []string{"oricli_core/skills", "../oricli_core/skills"} {
			if st, err := os.Stat(cand); err == nil && st.IsDir() {
				skillsDirs = []string{cand}
				break
			}
		}
	}
	agentsDirs := splitDirs(os.Getenv("ORI_AGENTS_DIR"))
	if len(agentsDirs) == 0 {
		for _, cand := range []string{".github/agents", "../.github/agents"} {
			if st, err := os.Stat(cand); err == nil && st.IsDir() {
				agentsDirs = []string{cand}
				break
			}
		}
	}

	forgeMax := 16
	if v := os.Getenv("ORI_FORGE_MAX_TOOLS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			forgeMax = n
		}
	}
	forgeTTL := 30 * time.Minute
	if v := os.Getenv("ORI_FORGE_TTL_MIN"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			forgeTTL = time.Duration(n) * time.Minute
		}
	}

	// Comma-separated only — origins contain "://" so colon splitting breaks URLs.
	corsOrigins := splitCSV(os.Getenv("ORI_CORS_ORIGINS"))

	return Config{
		Port:            port,
		CapsuleKey:      os.Getenv("ORI_CAPSULE_KEY"),
		DefaultProvider: defProv,
		OpenCodeBaseURL: ocBase,
		MemoryDir:       memDir,
		MemoryKey:       os.Getenv("ORI_MEMORY_ENCRYPTION_KEY"),
		MaxSessionTurns: maxTurns,
		GoshEnabled:     goshEnabled,
		GoshWorkspace:   goshWS,
		GoshForceMem:    goshForceMem,
		GoshExecTimeout: goshTimeout,
		SkillsDirs:      skillsDirs,
		AgentsDirs:      agentsDirs,
		ForgeMaxTools:   forgeMax,
		ForgeTTL:        forgeTTL,
		CORSOrigins:     corsOrigins,
	}
}

func splitDirs(v string) []string {
	if strings.TrimSpace(v) == "" {
		return nil
	}
	parts := strings.Split(v, ":")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

func splitCSV(v string) []string {
	if strings.TrimSpace(v) == "" {
		return nil
	}
	parts := strings.Split(v, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}
