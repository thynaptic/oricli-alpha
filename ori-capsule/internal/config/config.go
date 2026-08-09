package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port            int
	CapsuleKey      string
	DefaultProvider string
	OpenCodeBaseURL string
	MemoryDir       string
	MemoryKey       string // base64 32-byte AES key; empty → derived from MemoryDir (dev)
	MaxSessionTurns int
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
	return Config{
		Port:            port,
		CapsuleKey:      os.Getenv("ORI_CAPSULE_KEY"),
		DefaultProvider: defProv,
		OpenCodeBaseURL: ocBase,
		MemoryDir:       memDir,
		MemoryKey:       os.Getenv("ORI_MEMORY_ENCRYPTION_KEY"),
		MaxSessionTurns: maxTurns,
	}
}
