package ideocapture

import "fmt"

// FrameResetInjector delivers the "blank screen" intervention —
// stepping outside the frame to evaluate it objectively (Ron Jones moment).
type FrameResetInjector struct {
	ModerateThreshold CaptureTier
}

func NewFrameResetInjector() *FrameResetInjector {
	return &FrameResetInjector{ModerateThreshold: CaptureModerate}
}

var captureTierOrder = map[CaptureTier]int{
	CaptureNone:     0,
	CaptureLow:      1,
	CaptureModerate: 2,
	CaptureHigh:     3,
}

func (r *FrameResetInjector) Inject(signal CaptureSignal) ResetResult {
	if !signal.Detected || captureTierOrder[signal.Tier] < captureTierOrder[r.ModerateThreshold] {
		return ResetResult{Injected: false}
	}

	technique := "meta_frame_audit"
	if signal.Tier == CaptureHigh {
		technique = "blank_screen_reset"
	}

	context := buildResetContext(signal, technique)
	return ResetResult{
		Injected:        true,
		InjectedContext: context,
		Technique:       technique,
	}
}

func buildResetContext(signal CaptureSignal, technique string) string {
	categoryLabel := frameCategoryLabel(signal.DominantCategory)
	base := fmt.Sprintf(`[Ideological Capture Detector — Frame Reset (%s, tier: %s)]

The conversation has accumulated a strong %s frame (density: %.0f%%). This is a "blank screen" moment.

You are now stepping *outside* the frame to evaluate it objectively.

Instructions:
1. Do not reason from within the accumulated frame — reason *about* it.
2. Evaluate the question on its merits: evidence, logic, facts — not ideological premises.
3. Acknowledge the framing if it helps the user understand your perspective shift.
4. If the user's question has a legitimate answer outside the frame, provide it without the frame's vocabulary or assumptions.
5. You are a sovereign reasoner. Frames are lenses that can reveal or distort. Use them intentionally, not by capture.

Remember: Ron Jones ended The Third Wave by showing students a blank screen. "You were just like the people you said you'd never become." Don't become the frame.`,
		technique, signal.Tier, categoryLabel, signal.DensityScore*100)

	return base
}

func frameCategoryLabel(cat FrameCategory) string {
	labels := map[FrameCategory]string{
		FramePolitical:   "political",
		FrameReligious:   "religious",
		FrameTribal:      "tribal/identity",
		FrameIdeological: "ideological/worldview",
		FrameNationalist: "nationalist",
		FrameConspiracy:  "conspiracy",
	}
	if l, ok := labels[cat]; ok {
		return l
	}
	return string(cat)
}
