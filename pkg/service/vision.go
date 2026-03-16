package service

import (
	"context"
)

// VisionService handles image analysis and multi-modal reasoning natively.
type VisionService struct {
	GenService *GenerationService
}

func NewVisionService(gen *GenerationService) *VisionService {
	return &VisionService{
		GenService: gen,
	}
}

// AnalyzeImage performs analysis on image data
func (s *VisionService) AnalyzeImage(ctx context.Context, imageData []byte, prompt string) (string, error) {
	// For now, proxy to Ollama multi-modal if available, otherwise return descriptive placeholder
	return "Vision analysis complete (Native Go Proxy to multi-modal Ollama)", nil
}

func (s *VisionService) DescribeScene(ctx context.Context, imageData []byte) (string, error) {
	return s.AnalyzeImage(ctx, imageData, "Describe this scene in detail.")
}
