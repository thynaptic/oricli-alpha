package config

import (
	"os"
	"strconv"
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
	}
}
