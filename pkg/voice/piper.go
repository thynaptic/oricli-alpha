package voice

import (
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// --- Pillar 51: Affective Voice Synthesis (Piper) ---
// Translates internal resonance and energy into modulated speech.

type VoicePiperService struct {
	BinaryPath string
	ModelPath  string
	WSHub      interface {
		BroadcastEvent(eventType string, payload interface{})
	}
}

func NewVoicePiperService(binary, model string, hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) *VoicePiperService {
	return &VoicePiperService{
		BinaryPath: binary,
		ModelPath:  model,
		WSHub:      hub,
	}
}

// InjectWSHub allows late-binding of the WebSocket hub.
func (s *VoicePiperService) InjectWSHub(hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) {
	s.WSHub = hub
}

// Synthesize generates audio from text, modulated by affective metrics.
func (s *VoicePiperService) Synthesize(text string, resonance float32, energy float32, key string) {
	if text == "" || s.BinaryPath == "" || s.ModelPath == "" {
		return
	}

	// 1. Affective Modulation Mapping
	// Length Scale (Speed): 1.0 is default. Lower is faster.
	// We map high resonance (1.0) to fast (0.8) and low (0.0) to slow (1.5).
	lengthScale := 1.5 - (float64(resonance) * 0.7)

	// Noise Scale: Controls voice variance. High energy = more dynamic.
	noiseScale := 0.6 + (float64(energy) * 0.4)

	// 2. Prepare Output Buffer
	tmpFile := filepath.Join(os.TempDir(), fmt.Sprintf("ori_voice_%d.wav", os.Getpid()))
	
	// 3. Execute Piper
	// Format: echo "text" | ./piper --model voice.onnx --output_file out.wav --length_scale X --noise_scale Y
	cmd := exec.Command(s.BinaryPath, 
		"--model", s.ModelPath, 
		"--output_file", tmpFile,
		"--length_scale", fmt.Sprintf("%.2f", lengthScale),
		"--noise_scale", fmt.Sprintf("%.2f", noiseScale),
	)
	cmd.Stdin = strings.NewReader(text)

	if err := cmd.Run(); err != nil {
		log.Printf("[Voice] Piper synthesis failed: %v", err)
		return
	}

	// 4. Encode and Stream
	audioData, err := os.ReadFile(tmpFile)
	if err != nil {
		log.Printf("[Voice] Failed to read synthesized audio: %v", err)
		return
	}

	encoded := base64.StdEncoding.EncodeToString(audioData)
	
	if s.WSHub != nil {
		s.WSHub.BroadcastEvent("audio_sync", map[string]interface{}{
			"audio": encoded,
			"mime":  "audio/wav",
			"text":  text,
		})
	}

	// 5. Cleanup
	os.Remove(tmpFile)
	log.Printf("[Voice] Synthesized and streamed audio for turn. (Speed: %.2f, Energy: %.2f)", lengthScale, noiseScale)
}
