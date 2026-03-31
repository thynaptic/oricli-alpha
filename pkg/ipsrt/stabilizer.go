package ipsrt

import "fmt"

// RhythmStabilizer builds IPSRT-informed stabilization injections.
type RhythmStabilizer struct{}

func NewRhythmStabilizer() *RhythmStabilizer { return &RhythmStabilizer{} }

var stabilizationPrompts = map[RhythmDisruptionType]string{
	SleepDisruption: "The user's sleep rhythm appears disrupted. Gently acknowledge this, then ground your response in the IPSRT principle that irregular sleep is a known mood destabilizer — not a personal failing. Encourage one small, consistent anchor (e.g., a fixed wake time) rather than overhauling everything at once.",
	RoutineBreak:    "The user's daily routine has broken down. Acknowledge the disorientation that comes with lost structure. Ground your response in the IPSRT insight that social rhythms are protective: suggest anchoring just one or two activities at consistent times as a starting point, not a complete rebuild.",
	MealDisruption:  "The user's eating pattern appears irregular. Acknowledge it without judgment. Remind that irregular meal timing perturbs biological rhythms in ways similar to irregular sleep — one consistent mealtime per day is a meaningful anchor.",
	SocialIsolation: "The user appears socially withdrawn or isolated. Acknowledge this with warmth. Ground your response in the IPSRT principle that regular first social contact (even brief) is a key Social Rhythm Metric anchor — small consistent contact matters more than grand re-engagement.",
	ScheduleChaos:   "The user's schedule appears chaotic or unpredictable. Acknowledge the cognitive and emotional cost of that instability. Ground your response in the IPSRT idea that predictability itself is protective — help them identify even one predictable daily anchor they could commit to.",
}

// Stabilize selects the highest-priority injection for the scan.
func (s *RhythmStabilizer) Stabilize(scan *RhythmScan) string {
	if !scan.Disrupted || len(scan.Signals) == 0 {
		return ""
	}
	// Priority: sleep > schedule > routine > meal > social
	priority := []RhythmDisruptionType{SleepDisruption, ScheduleChaos, RoutineBreak, MealDisruption, SocialIsolation}
	sigMap := map[RhythmDisruptionType]bool{}
	for _, sig := range scan.Signals {
		sigMap[sig.DisruptionType] = true
	}
	for _, dt := range priority {
		if sigMap[dt] {
			return fmt.Sprintf("[IPSRT Rhythm Stabilizer] %s", stabilizationPrompts[dt])
		}
	}
	return ""
}
