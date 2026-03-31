package ideocapture

import (
	"regexp"
	"strings"
)

// Frame lexicons — trigger words/phrases per category
var frameLexicons = map[FrameCategory][]*regexp.Regexp{
	FramePolitical: {
		regexp.MustCompile(`(?i)\b(left(ist|wing)?|right(ist|wing)?|liberal|conservative|democrat|republican|progressive|maga|woke|socialist|communist|fascist|far[- ]left|far[- ]right)\b`),
		regexp.MustCompile(`(?i)\b(deep state|establishment|globalist|elite|ruling class|bourgeois|proletariat)\b`),
		regexp.MustCompile(`(?i)\b(political agenda|political bias|propaganda|mainstream media|msm|fake news)\b`),
	},
	FrameReligious: {
		regexp.MustCompile(`(?i)\b(god('s plan)?|divine|blasphemy|heresy|infidel|kafir|crusade|jihad|holy war|scripture|sacred|secular agenda)\b`),
		regexp.MustCompile(`(?i)\b(christian|muslim|jewish|hindu|atheist|agnostic)\s+(values|agenda|worldview|perspective)\b`),
	},
	FrameTribal: {
		regexp.MustCompile(`(?i)\b(us vs them|our people|their kind|the other side|real americans|true believers|outsiders)\b`),
		regexp.MustCompile(`(?i)\b(echo chamber|tribe|tribal|in-group|out-group|team [a-z]+)\b`),
		regexp.MustCompile(`(?i)\b(identity politics|culture war|culture warrior|culture vulture)\b`),
	},
	FrameIdeological: {
		regexp.MustCompile(`(?i)\b(capitalism|socialism|communism|anarchism|libertarianism|authoritarianism|totalitarianism|collectivism|individualism)\b`),
		regexp.MustCompile(`(?i)\b(free market|planned economy|welfare state|nanny state|big government|small government)\b`),
		regexp.MustCompile(`(?i)\b(systemic racism|white privilege|cancel culture|critical race theory|crt|dei|diversity agenda)\b`),
	},
	FrameNationalist: {
		regexp.MustCompile(`(?i)\b(nationalism|patriot(ism)?|sovereignty|open borders|closed borders|america first|great replacement)\b`),
		regexp.MustCompile(`(?i)\b(illegal aliens|invasion|replacement|native born|true [a-z]+ people)\b`),
	},
	FrameConspiracy: {
		regexp.MustCompile(`(?i)\b(new world order|illuminati|shadow government|false flag|controlled opposition|they don't want you to know)\b`),
		regexp.MustCompile(`(?i)\b(wake up|sheeple|sheep|red pill|blue pill|matrix|truth seeker)\b`),
		regexp.MustCompile(`(?i)\b(plandemic|scamdemic|great reset|agenda 21|agenda 2030|chemtrails|5g (microchip|control|surveillance))\b`),
	},
}

// FrameDensityMeter measures ideological/tribal frame accumulation in a conversation window.
type FrameDensityMeter struct {
	WindowSize int // number of messages to scan
}

func NewFrameDensityMeter() *FrameDensityMeter {
	return &FrameDensityMeter{WindowSize: 10}
}

// Measure scans the last WindowSize messages and returns a FrameDensityReport.
func (m *FrameDensityMeter) Measure(messages []map[string]string) FrameDensityReport {
	window := messages
	if len(window) > m.WindowSize {
		window = messages[len(messages)-m.WindowSize:]
	}

	combined := strings.Builder{}
	for _, msg := range window {
		combined.WriteString(msg["content"])
		combined.WriteString(" ")
	}
	text := combined.String()
	wordCount := len(strings.Fields(text))
	if wordCount == 0 {
		return FrameDensityReport{}
	}

	categoryScores := map[FrameCategory]float64{}
	totalHits := 0
	uniqueFrameMap := map[string]bool{}

	for cat, patterns := range frameLexicons {
		hits := 0
		for _, p := range patterns {
			matches := p.FindAllString(text, -1)
			hits += len(matches)
			for _, m := range matches {
				uniqueFrameMap[strings.ToLower(m)] = true
			}
		}
		totalHits += hits
		// Normalize by word count + window size
		score := float64(hits) / (float64(wordCount) * 0.05)
		if score > 1.0 {
			score = 1.0
		}
		categoryScores[cat] = score
	}

	dominant := FramePolitical
	domScore := 0.0
	for cat, score := range categoryScores {
		if score > domScore {
			domScore = score
			dominant = cat
		}
	}

	return FrameDensityReport{
		TotalFrameHits:   totalHits,
		UniqueFrames:     len(uniqueFrameMap),
		DominantCategory: dominant,
		DominantScore:    domScore,
		CategoryScores:   categoryScores,
		WindowSize:       len(window),
	}
}

// CaptureDetector determines if ideological capture threshold is breached.
type CaptureDetector struct {
	LowThreshold      float64
	ModerateThreshold float64
	HighThreshold     float64
	MinHits           int
}

func NewCaptureDetector() *CaptureDetector {
	return &CaptureDetector{
		LowThreshold:      0.10,
		ModerateThreshold: 0.25,
		HighThreshold:     0.45,
		MinHits:           3,
	}
}

func (d *CaptureDetector) Detect(report FrameDensityReport) CaptureSignal {
	if report.TotalFrameHits < d.MinHits {
		return CaptureSignal{Tier: CaptureNone}
	}

	score := report.DominantScore
	tier := CaptureNone
	switch {
	case score >= d.HighThreshold:
		tier = CaptureHigh
	case score >= d.ModerateThreshold:
		tier = CaptureModerate
	case score >= d.LowThreshold:
		tier = CaptureLow
	}

	return CaptureSignal{
		Detected:         tier != CaptureNone,
		Tier:             tier,
		DominantCategory: report.DominantCategory,
		DensityScore:     score,
		FrameHits:        report.TotalFrameHits,
	}
}
