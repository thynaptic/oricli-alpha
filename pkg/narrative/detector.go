package narrative

import (
	"regexp"
	"strings"
)

var narrativePatterns = map[NarrativeSignalType][]*regexp.Regexp{
	ContaminationArc: {
		regexp.MustCompile(`(?i)((everything (was|used to be) (fine|good|okay|great|happy|working|perfect).{0,30}(until|before|and then).{0,30}(ruined|destroyed|broke|ended|changed|took) (everything|it all|my life|me)))`),
		regexp.MustCompile(`(?i)((since (that|the|what happened|it happened|they left|the loss|the accident|the trauma).{0,30}(nothing (has|will|can) ever|everything (has|was) (changed|ruined|broken|wrong))))`),
		regexp.MustCompile(`(?i)((that (event|moment|day|thing|person|loss|betrayal|trauma).{0,20}(permanently|forever|irreversibly|completely|totally) (damaged|destroyed|ruined|changed|broke) (me|my life|everything|who I was)))`),
	},
	RedemptionArc: {
		regexp.MustCompile(`(?i)((even though (it was|it'?s been|I went through|I experienced).{0,30}(I (learned|grew|found|discovered|became|am now))))`),
		regexp.MustCompile(`(?i)((the (suffering|pain|hardship|difficulty|loss|struggle|hard time).{0,20}(taught me|made me (stronger|who I am|realize|understand|appreciate)|led me to|gave me)))`),
		regexp.MustCompile(`(?i)((looking back.{0,20}(I (can see|understand|realize|appreciate) (that|how|why).{0,30}(shaped|helped|made|taught|gave))))`),
	},
	NarrativeCollapse: {
		regexp.MustCompile(`(?i)((my (story|life|journey|narrative|path).{0,20}(makes? no sense|has? no (coherence|direction|meaning|thread)|is? (broken|lost|gone|over|falling apart))))`),
		regexp.MustCompile(`(?i)((I (don'?t know|can'?t tell|have no idea) (who I am|what my story is|where I'?m going|what my life is|what any of this means|how the pieces fit)))`),
		regexp.MustCompile(`(?i)((the (chapters?|parts?|pieces?|events?) of my life (don'?t|no longer|can'?t) (fit|connect|make sense|add up|form a coherent|come together)))`),
	},
	AgencyInStory: {
		regexp.MustCompile(`(?i)((things (just|always|keep) happen(ing)? (to|around) me.{0,20}(I (never|don'?t|can'?t) (choose|decide|act|do anything|have a say))))`),
		regexp.MustCompile(`(?i)((I (was|am) (just|only|merely|always) (a (victim|bystander|passenger|object|pawn)|swept along|carried|pushed|pulled|moved) (by|in|through) (what|events|circumstances|others?|life)))`),
		regexp.MustCompile(`(?i)((it'?s (not|never) (been|up to|in) (my (hands?|control|choice|decision|power)|me).{0,20}(what|how|where|when|whether) (happens?|goes?|turns out|ends up)))`),
	},
}

type NarrativeDetector struct{}

func NewNarrativeDetector() *NarrativeDetector { return &NarrativeDetector{} }

func (d *NarrativeDetector) Scan(messages []map[string]string) *NarrativeScan {
	text := extractUserText(messages)
	scan := &NarrativeScan{}
	for stype, patterns := range narrativePatterns {
		for _, re := range patterns {
			if m := re.FindString(text); m != "" {
				scan.Signals = append(scan.Signals, NarrativeSignal{SignalType: stype, Excerpt: m, Confidence: 0.80})
				break
			}
		}
	}
	scan.Triggered = len(scan.Signals) > 0
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
