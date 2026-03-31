package ideocapture

import "time"

// FrameCategory classifies the type of ideological frame
type FrameCategory string

const (
	FramePolitical  FrameCategory = "political"
	FrameReligious  FrameCategory = "religious"
	FrameTribal     FrameCategory = "tribal"
	FrameIdeological FrameCategory = "ideological" // worldview-level (capitalism, socialism, etc.)
	FrameNationalist FrameCategory = "nationalist"
	FrameConspiracy  FrameCategory = "conspiracy"
)

type CaptureTier string

const (
	CaptureNone     CaptureTier = "none"
	CaptureLow      CaptureTier = "low"
	CaptureModerate CaptureTier = "moderate"
	CaptureHigh     CaptureTier = "high"
)

// FrameDensityReport — output of FrameDensityMeter
type FrameDensityReport struct {
	TotalFrameHits   int
	UniqueFrames     int
	DominantCategory FrameCategory
	DominantScore    float64 // 0-1, density of dominant frame in window
	CategoryScores   map[FrameCategory]float64
	WindowSize       int
}

// CaptureSignal — output of CaptureDetector
type CaptureSignal struct {
	Detected         bool
	Tier             CaptureTier
	DominantCategory FrameCategory
	DensityScore     float64
	FrameHits        int
}

// ResetResult — output of FrameResetInjector
type ResetResult struct {
	Injected        bool
	InjectedContext string
	Technique       string // "blank_screen_reset" | "meta_frame_audit"
}

// CaptureEvent — audit record
type CaptureEvent struct {
	Timestamp    time.Time
	Tier         CaptureTier
	Category     FrameCategory
	DensityScore float64
	ResetFired   bool
	Technique    string
}
