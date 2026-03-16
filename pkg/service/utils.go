package service

import "os"

// getEnv gets an environment variable or returns a fallback value
func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

// ToFloat64 converts any numeric type to float64
func ToFloat64(v interface{}) float64 {
	switch i := v.(type) {
	case float64:
		return i
	case float32:
		return float64(i)
	case int:
		return float64(i)
	case int64:
		return float64(i)
	default:
		return 0.0
	}
}
