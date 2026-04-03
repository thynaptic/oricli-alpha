package arte

import (
	"math"
	"sync"
	"time"
)

const (
	// windowSize is how many inference samples the detector keeps in its sliding window.
	windowSize = 20

	// minSamplesForDetection — below this, stay in Calm (not enough signal).
	minSamplesForDetection = 3

	// hysteresisThreshold — a state must outscore the current state by this margin
	// to trigger a transition. Prevents rapid flapping.
	hysteresisThreshold = 0.15

	// maxStateAge — if the state hasn't been reinforced in this long, decay it toward Calm.
	maxStateAge = 5 * time.Minute
)

// InferenceSample is one data point from a Sovereign pipeline run.
type InferenceSample struct {
	Duration    time.Duration
	Success     bool
	TokenCount  int     // approx tokens generated (0 = unknown)
	Complexity  float32 // 0.0-1.0 — caller's estimate of query complexity
	RecordedAt  time.Time
}

// Detector is the ARTE state machine.
// Thread-safe — safe to call UpdateFromInference concurrently.
type Detector struct {
	mu      sync.Mutex
	samples []InferenceSample

	current   ARTEState
	intensity float32
	stability float32
	lastShift time.Time
}

// NewDetector returns a Detector in the Calm baseline state.
func NewDetector() *Detector {
	return &Detector{
		current:   StateCalm,
		intensity: 0.5,
		stability: 1.0,
		lastShift: time.Now(),
	}
}

// UpdateFromInference records a new inference outcome and re-evaluates state.
func (d *Detector) UpdateFromInference(s InferenceSample) {
	d.mu.Lock()
	defer d.mu.Unlock()

	if s.RecordedAt.IsZero() {
		s.RecordedAt = time.Now()
	}

	// Maintain sliding window
	d.samples = append(d.samples, s)
	if len(d.samples) > windowSize {
		d.samples = d.samples[len(d.samples)-windowSize:]
	}

	d.reEvaluate()
}

// Read returns the current ARTE reading (non-blocking snapshot).
func (d *Detector) Read() ARTEReading {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Passive decay toward Calm if the state hasn't been reinforced
	if time.Since(d.lastShift) > maxStateAge && d.current != StateCalm {
		d.intensity = float32(math.Max(0.3, float64(d.intensity)-0.1))
		if d.intensity <= 0.3 {
			d.current = StateCalm
			d.intensity = 0.5
			d.lastShift = time.Now()
		}
	}

	return ARTEReading{
		State:     d.current,
		Intensity: d.intensity,
		Stability: d.stability,
		Score:     ScoreFor(d.current, d.intensity),
		Palette:   PaletteFor(d.current),
	}
}

// reEvaluate scores all candidate states and picks the winner (hysteresis-gated).
// Must be called with d.mu held.
func (d *Detector) reEvaluate() {
	if len(d.samples) < minSamplesForDetection {
		return
	}

	recent := d.samples
	scores := map[ARTEState]float32{
		StateCalm:       0.0,
		StateFocused:    0.0,
		StateReflective: 0.0,
		StateEnergized:  0.0,
		StateFatigued:   0.0,
	}

	// ── Metrics extracted from sliding window ──────────────────────────────────

	// Success rate
	successes := 0
	for _, s := range recent {
		if s.Success {
			successes++
		}
	}
	successRate := float32(successes) / float32(len(recent))

	// Average duration (seconds)
	var totalSecs float64
	for _, s := range recent {
		totalSecs += s.Duration.Seconds()
	}
	avgSecs := totalSecs / float64(len(recent))

	// Duration trend: compare last half to first half
	half := len(recent) / 2
	var firstHalfAvg, secondHalfAvg float64
	if half > 0 {
		for _, s := range recent[:half] {
			firstHalfAvg += s.Duration.Seconds()
		}
		firstHalfAvg /= float64(half)
		for _, s := range recent[half:] {
			secondHalfAvg += s.Duration.Seconds()
		}
		secondHalfAvg /= float64(len(recent) - half)
	}
	speedingUp := secondHalfAvg < firstHalfAvg*0.85

	// Average token count (proxy for response richness)
	var totalTokens int
	for _, s := range recent {
		totalTokens += s.TokenCount
	}
	avgTokens := float32(totalTokens) / float32(len(recent))

	// Average complexity
	var totalComplexity float32
	for _, s := range recent {
		totalComplexity += s.Complexity
	}
	avgComplexity := totalComplexity / float32(len(recent))

	// Recency: weight the last 5 samples more
	lastN := recent
	if len(recent) > 5 {
		lastN = recent[len(recent)-5:]
	}
	var recentSuccesses int
	for _, s := range lastN {
		if s.Success {
			recentSuccesses++
		}
	}
	recentSuccessRate := float32(recentSuccesses) / float32(len(lastN))

	// ── State scoring ──────────────────────────────────────────────────────────

	// FATIGUED: poor success rate, slow responses, degraded recent performance
	if successRate < 0.45 {
		scores[StateFatigued] += 0.45
	}
	if recentSuccessRate < 0.35 {
		scores[StateFatigued] += 0.30
	}
	if avgSecs > 30.0 && successRate < 0.6 {
		scores[StateFatigued] += 0.15
	}

	// ENERGIZED: high recent success, speeding up, fast responses
	if recentSuccessRate > 0.85 {
		scores[StateEnergized] += 0.35
	}
	if speedingUp && successRate > 0.75 {
		scores[StateEnergized] += 0.25
	}
	if avgSecs < 6.0 && successRate > 0.8 {
		scores[StateEnergized] += 0.20
	}

	// FOCUSED: consistent success, moderate pace, low variance
	durationVariance := durationVariance(recent)
	if successRate > 0.75 && durationVariance < 8.0 {
		scores[StateFocused] += 0.30
	}
	if successRate > 0.85 {
		scores[StateFocused] += 0.20
	}
	if avgComplexity > 0.5 && successRate > 0.7 {
		scores[StateFocused] += 0.20
	}

	// REFLECTIVE: high token output (long responses), complex topics, moderate pace
	if avgTokens > 300 {
		scores[StateReflective] += 0.30
	}
	if avgComplexity > 0.65 {
		scores[StateReflective] += 0.25
	}
	if avgSecs > 10.0 && successRate > 0.7 {
		scores[StateReflective] += 0.15
	}

	// CALM: default gravity when no strong signal
	scores[StateCalm] += 0.15

	// ── Pick winner (hysteresis-gated) ─────────────────────────────────────────
	var best ARTEState = StateCalm
	var bestScore float32
	for state, score := range scores {
		if score > bestScore {
			bestScore = score
			best = state
		}
	}

	currentScore := scores[d.current]
	if best != d.current && bestScore-currentScore >= hysteresisThreshold {
		d.current = best
		d.lastShift = time.Now()
		d.stability = 0.4 // low stability during transition
	} else {
		// Reinforce current state stability
		d.stability = float32(math.Min(1.0, float64(d.stability)+0.05))
	}

	// Intensity from winning score (clamped to [0.3, 1.0])
	d.intensity = float32(math.Min(1.0, math.Max(0.3, float64(bestScore))))
}

// durationVariance returns variance in seconds² across samples.
func durationVariance(samples []InferenceSample) float64 {
	if len(samples) < 2 {
		return 0
	}
	var sum float64
	for _, s := range samples {
		sum += s.Duration.Seconds()
	}
	mean := sum / float64(len(samples))
	var variance float64
	for _, s := range samples {
		d := s.Duration.Seconds() - mean
		variance += d * d
	}
	return variance / float64(len(samples))
}
