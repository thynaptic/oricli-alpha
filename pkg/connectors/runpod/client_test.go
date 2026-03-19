package runpod

import (
	"os"
	"testing"
	"github.com/joho/godotenv" // I'll need to check if I have this or use a simple loader
)

func TestClient_GetGPUTypes(t *testing.T) {
	// Attempt to load .env from the project root
	// Since we are in pkg/connectors/runpod, we go up 3 levels
	godotenv.Load("../../../.env")
	
	apiKey := os.Getenv("OricliAlpha_Key")
	if apiKey == "" {
		t.Skip("OricliAlpha_Key not set in environment, skipping integration test")
	}

	client := NewClient(apiKey)
	gpus, err := client.GetGPUTypes()
	if err != nil {
		t.Fatalf("GetGPUTypes failed: %v", err)
	}

	if len(gpus) == 0 {
		t.Error("Expected at least one GPU type, got none")
	}

	t.Logf("Found %d GPU types. First: %s", len(gpus), gpus[0].DisplayName)
}

func TestClient_GetPods(t *testing.T) {
	godotenv.Load("../../../.env")
	apiKey := os.Getenv("OricliAlpha_Key")
	if apiKey == "" {
		t.Skip("OricliAlpha_Key not set in environment, skipping integration test")
	}

	client := NewClient(apiKey)
	pods, err := client.GetPods()
	if err != nil {
		t.Fatalf("GetPods failed: %v", err)
	}

	t.Logf("Found %d pods.", len(pods))
}
