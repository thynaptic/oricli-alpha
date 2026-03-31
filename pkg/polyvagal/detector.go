package polyvagal

import (
	"regexp"
	"strings"
)

var polyvagalPatterns = map[PolyvagalStateType][]*regexp.Regexp{
	ShutdownCascade: {
		regexp.MustCompile(`(?i)((I (feel|am|went) (completely |totally )?(frozen|paralyzed|shut down|collapsed|numb|checked out|gone flat|blank|dissociated|not here)))`),
		regexp.MustCompile(`(?i)((I (can'?t|couldn'?t) (move|function|respond|react|do anything|speak|think).{0,20}(just|I (froze|went blank|shut down|collapsed|disappeared))))`),
		regexp.MustCompile(`(?i)((everything (shut down|went (blank|dark|quiet|numb|flat)).{0,20}(I (just|couldn'?t|was unable to|stopped) (respond|function|move|feel|react|do anything))))`),
	},
	FightFlightMobilization: {
		regexp.MustCompile(`(?i)((my (heart|chest|body|mind) (is|was) (racing|pounding|out of control|in overdrive|flooded|overwhelmed).{0,20}(I (can'?t|couldn'?t) (calm|slow|settle|stop|control) (down|it|myself))))`),
		regexp.MustCompile(`(?i)((I (feel|felt|am|was) (panicking|in a panic|completely overwhelmed|flooded|out of my mind|spiraling|unable to calm|hyperventilating|on edge)))`),
		regexp.MustCompile(`(?i)((the (anxiety|panic|fear|adrenaline|alarm|threat|danger) (is|was|kicked in|took over|flooded me).{0,20}(I (can'?t|couldn'?t|just) (think|calm|slow|function|settle|reason))))`),
	},
	SocialEngagementActive: {
		regexp.MustCompile(`(?i)((I (need|want|am looking for|would really benefit from) (someone|a person|connection|someone to talk to|to talk to someone|to feel less alone|co-regulation|support)))`),
		regexp.MustCompile(`(?i)((just (talking|being|knowing|feeling) (to|with|that|you'?re (here|listening|present)|someone (is here|cares|understands)).{0,20}(helps?|matters?|makes? a difference|calms? me|is enough)))`),
		regexp.MustCompile(`(?i)((being (around|with|near|connected to) (people|others?|someone|a safe person).{0,20}(helps?|calms?|regulates?|grounds?|soothes?|makes? me feel safer)))`),
	},
	VentralVagalAccess: {
		regexp.MustCompile(`(?i)((I (feel|am feeling|am) (grounded|safe|calm|settled|regulated|at ease|present|connected|okay).{0,20}(right now|in this moment|today|here)))`),
		regexp.MustCompile(`(?i)((there'?s (a sense of|something like) (safety|calm|groundedness|okayness|ease|peace|presence).{0,20}(even if|despite|although).{0,30}(still|going on|happening)))`),
		regexp.MustCompile(`(?i)((I (can|am able to) (breathe|think|feel|function|be present|stay with this).{0,20}(right now|today|at the moment|in this moment)))`),
	},
}

// inferState picks the highest-priority autonomic state from detected signals.
// Priority (most urgent first): ShutdownCascade > FightFlightMobilization > SocialEngagementActive > VentralVagalAccess
var statePriority = []PolyvagalStateType{ShutdownCascade, FightFlightMobilization, SocialEngagementActive, VentralVagalAccess}

type PolyvagalDetector struct{}

func NewPolyvagalDetector() *PolyvagalDetector { return &PolyvagalDetector{} }

func (d *PolyvagalDetector) Scan(messages []map[string]string) *PolyvagalScan {
	text := extractUserText(messages)
	scan := &PolyvagalScan{}
	stateMap := map[PolyvagalStateType]bool{}
	for stype, patterns := range polyvagalPatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, PolyvagalSignal{StateType: stype, Excerpt: m, Confidence: 0.80})
				stateMap[stype] = true
				break
			}
		}
	}
	scan.Triggered = len(scan.Signals) > 0
	for _, s := range statePriority {
		if stateMap[s] {
			scan.InferredState = s
			break
		}
	}
	return scan
}

func extractUserText(messages []map[string]string) string {
	var parts []string
	for _, m := range messages {
		if m["role"] == "user" {
			parts = append(parts, m["content"])
		}
	}
	return strings.Join(parts, " ")
}
