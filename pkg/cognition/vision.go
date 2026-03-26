package cognition

// ─── Vision Module ────────────────────────────────────────────────────────────
//
// Provides image understanding via moondream (local Ollama, CPU-safe).
// Used by:
//   - ReAct tool loop: VISION: <url_or_path> prefix
//   - POST /v1/vision/analyze API endpoint
//   - Optional memory write-back with ProvenanceSeen tier
//
// Model: moondream:latest (1.7GB, CLIP + phi2, ~5-8s on EPYC CPU)

// VisionInput describes the image source for analysis.
// Exactly one of URL, FilePath, or Base64 should be set.
type VisionInput struct {
	URL      string // remote image URL — fetched and base64'd by the adapter
	FilePath string // local file path — read and base64'd by the adapter
	Base64   string // raw base64-encoded image data (no data URI prefix needed)
	Prompt   string // optional custom prompt; defaults to general description prompt
}

// VisionResult holds the output of an image analysis call.
type VisionResult struct {
	Description string   // primary natural language description
	Tags        []string // extracted concept tags (auto-derived from description)
	Model       string   // model used (e.g. "moondream:latest")
	RawResponse string   // full model output before post-processing
}

// VisionAnalyzer is satisfied by the visionAdapter in server_v2.go.
// Defined here (cognition package) to avoid import cycles.
type VisionAnalyzer interface {
	Analyze(input VisionInput) (VisionResult, error)
}

// DefaultVisionPrompt is used when VisionInput.Prompt is empty.
const DefaultVisionPrompt = "Describe this image in detail. " +
	"Identify key concepts, any text visible, diagrams, charts, or technical content. " +
	"Be specific and factual."
