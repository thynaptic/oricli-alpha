package vdi

import (
	"context"
	"fmt"
	"regexp"
	"strconv"
)

// --- Pillar 49: Vision Grounding Service ---
// Translates visual element descriptions into pixel coordinates using Qwen2.5-VL.

// Generator defines the interface required for vision-based generation.
type Generator interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

type GroundingBox struct {
	X1, Y1, X2, Y2 float64
}

func (b *GroundingBox) Center() (float64, float64) {
	return (b.X1 + b.X2) / 2.0, (b.Y1 + b.Y2) / 2.0
}

type VisionGroundingService struct {
	Gen   Generator
	Model string
}

func NewVisionGroundingService(gen Generator) *VisionGroundingService {
	return &VisionGroundingService{
		Gen:   gen,
		Model: "qwen2.5-vl:7b",
	}
}

// GetElementCoordinates takes a screenshot and description, returning the center [x, y].
func (s *VisionGroundingService) GetElementCoordinates(ctx context.Context, imageBase64 string, description string) (float64, float64, error) {
	prompt := fmt.Sprintf(`Detect the location of "%s" in this UI screenshot. 
Return the bounding box in the exact format: [x1, y1, x2, y2]. 
Use absolute pixel coordinates relative to the 1280x720 resolution.`, description)

	res, err := s.Gen.Generate(prompt, map[string]interface{}{
		"model":  s.Model,
		"images": []string{imageBase64},
	})
	if err != nil {
		return 0, 0, err
	}

	text, ok := res["text"].(string)
	if !ok {
		return 0, 0, fmt.Errorf("invalid response format from vision model")
	}

	// Parse coordinates [x1, y1, x2, y2]
	box, err := s.parseCoordinates(text)
	if err != nil {
		return 0, 0, fmt.Errorf("failed to parse grounding coordinates: %v (Model Output: %s)", err, text)
	}

	cx, cy := box.Center()
	return cx, cy, nil
}

func (s *VisionGroundingService) parseCoordinates(text string) (*GroundingBox, error) {
	re := regexp.MustCompile(`\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]`)
	matches := re.FindStringSubmatch(text)
	if len(matches) < 5 {
		return nil, fmt.Errorf("coordinates not found in output")
	}

	x1, _ := strconv.ParseFloat(matches[1], 64)
	y1, _ := strconv.ParseFloat(matches[2], 64)
	x2, _ := strconv.ParseFloat(matches[3], 64)
	y2, _ := strconv.ParseFloat(matches[4], 64)

	return &GroundingBox{X1: x1, Y1: y1, X2: x2, Y2: y2}, nil
}
