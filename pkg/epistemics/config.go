package epistemics

import (
	"os"
	"strconv"
	"strings"
)

var cfg = loadConfig()

type epConfig struct {
	Enabled   bool
	MaxIter   int
	Threshold float64
	Trace     bool
}

func loadConfig() epConfig {
	return epConfig{
		Enabled:   boolEnvEp("ORI_EPISTEMICS_ENABLED", true),
		MaxIter:   intEnvEp("ORI_EPISTEMICS_MAX_ITER", 2),
		Threshold: floatEnvEp("ORI_EPISTEMICS_ESCALATE_THRESHOLD", 0.65),
		Trace:     boolEnvEp("ORI_EPISTEMICS_TRACE", false),
	}
}

func boolEnvEp(key string, def bool) bool {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return def
	}
	return v == "1" || strings.EqualFold(v, "true")
}

func intEnvEp(key string, def int) int {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return def
	}
	return n
}

func floatEnvEp(key string, def float64) float64 {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return def
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return def
	}
	return f
}
