package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port              int
	CapsuleKey        string // optional gateway lock
	DefaultProvider   string
	OpenCodeBaseURL   string
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
	return Config{
		Port:            port,
		CapsuleKey:      os.Getenv("ORI_CAPSULE_KEY"),
		DefaultProvider: defProv,
		OpenCodeBaseURL: ocBase,
	}
}
