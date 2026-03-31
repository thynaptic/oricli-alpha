package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Config is the CLI configuration loaded from ~/.oricli/config.yaml.
// Environment variables and flags override file values.
type Config struct {
	Target string `yaml:"target"`  // e.g. http://localhost:8089
	APIKey string `yaml:"api_key"` // Bearer token
	Model  string `yaml:"model"`
	Stream bool   `yaml:"stream"`
}

const defaultTarget = "http://localhost:8089"
const defaultModel = "oricli-alpha"
const configDir = ".oricli"
const configFile = "config.yaml"

// LoadConfig loads config from ~/.oricli/config.yaml then applies env overrides.
func LoadConfig() (*Config, error) {
	cfg := &Config{
		Target: defaultTarget,
		Model:  defaultModel,
		Stream: true,
	}

	path, err := configPath()
	if err == nil {
		if data, err := os.ReadFile(path); err == nil {
			_ = yaml.Unmarshal(data, cfg)
		}
	}

	// Env overrides
	if v := os.Getenv("ORICLI_TARGET"); v != "" {
		cfg.Target = v
	}
	if v := os.Getenv("ORICLI_API_KEY"); v != "" {
		cfg.APIKey = v
	}
	if v := os.Getenv("ORICLI_MODEL"); v != "" {
		cfg.Model = v
	}

	return cfg, nil
}

// Save writes config to ~/.oricli/config.yaml.
func (c *Config) Save() error {
	path, err := configPath()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	data, err := yaml.Marshal(c)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0600)
}

func configPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot determine home dir: %w", err)
	}
	return filepath.Join(home, configDir, configFile), nil
}

// ConfigDir returns the ~/.oricli directory path.
func ConfigDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, configDir), nil
}
