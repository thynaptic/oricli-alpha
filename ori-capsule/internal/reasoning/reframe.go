package reasoning

import (
	"regexp"
	"strings"
)

// Cognition reframes — single system inject only (no full-regen retry).
// Kept as reasoning aids, not clinical therapy product.

type reframeSignal string

const (
	sigPseudoCertainty      reframeSignal = "pseudo_certainty"
	sigUnexaminedAssumption reframeSignal = "unexamined_assumption"
	sigBeggingTheQuestion   reframeSignal = "begging_the_question"
	sigFalseDefinition      reframeSignal = "false_definition"
	sigControlConflation    reframeSignal = "control_conflation"
	sigExternalAttachment   reframeSignal = "external_attachment"
	sigObstacleAvoidance    reframeSignal = "obstacle_avoidance"
	sigVirtueNeglect        reframeSignal = "virtue_neglect"
	sigContaminationArc     reframeSignal = "contamination_arc"
	sigNarrativeCollapse    reframeSignal = "narrative_collapse"
	sigAgencyInStory        reframeSignal = "agency_in_story"
	sigRedemptionArc        reframeSignal = "redemption_arc"
)

var reframePatterns = []struct {
	Sig reframeSignal
	Re  *regexp.Regexp
	Inj string
}{
	{sigPseudoCertainty, regexp.MustCompile(`(?i)\b(obviously|clearly|everyone knows|of course|it goes without saying)\b`),
		"[REASONING — PSEUDO-CERTAINTY] Treat “obviously” as a flag. Examine the claim: what evidence would count for/against it?"},
	{sigUnexaminedAssumption, regexp.MustCompile(`(?i)\b(assuming that|given that .{0,40}(it follows|we (must|should))|we all know that)\b`),
		"[REASONING — UNEXAMINED ASSUMPTION] Name the premise treated as given. Ask what would need to be true for the conclusion to hold."},
	{sigBeggingTheQuestion, regexp.MustCompile(`(?i)\b(it'?s (wrong|right|true|false) because it'?s (wrong|right|true|false))\b`),
		"[REASONING — CIRCULAR] Separate claim from justification; seek independent evidence."},
	{sigFalseDefinition, regexp.MustCompile(`(?i)\b(by definition|what .{0,20} really means|true (success|freedom|justice) means)\b`),
		"[REASONING — DEFINITION] Clarify the key term before arguing from it."},
	{sigControlConflation, regexp.MustCompile(`(?i)\b(I (can'?t|cannot) control .{0,40}(and it'?s (killing|crushing)|and I (can'?t|don'?t) (cope|handle)))\b`),
		"[REASONING — CONTROL] Separate what is choosable (judgments/actions) from what is not; focus energy on the former."},
	{sigExternalAttachment, regexp.MustCompile(`(?i)\b(my (happiness|peace).{0,20}(depends on|is tied to|requires))\b`),
		"[REASONING — ATTACHMENT] Note where wellbeing is tied to an external outcome; recover response authorship."},
	{sigObstacleAvoidance, regexp.MustCompile(`(?i)\b(the (obstacle|problem|barrier).{0,30}(means? I (can'?t|should|have to) (give up|stop|quit)))\b`),
		"[REASONING — OBSTACLE] Treat the impediment as material to work through, not proof the goal is invalid."},
	{sigVirtueNeglect, regexp.MustCompile(`(?i)\b(how I (respond|react).{0,20}(was|is) (determined|caused|dictated) by)\b`),
		"[REASONING — AGENCY] Circumstances set the stage; response quality is still authored."},
	{sigContaminationArc, regexp.MustCompile(`(?i)\b(everything (was|used to be) (fine|good).{0,30}(until|and then).{0,30}(ruined|destroyed|broke))\b`),
		"[REASONING — NARRATIVE] Permanent “everything ruined” arcs assign total meaning to one chapter; check what persisted."},
	{sigNarrativeCollapse, regexp.MustCompile(`(?i)\b(my (story|life).{0,20}(makes? no sense|has? no (coherence|direction|meaning)))\b`),
		"[REASONING — NARRATIVE] Coherence loss is not the end of authorship; start from small concrete true statements."},
	{sigAgencyInStory, regexp.MustCompile(`(?i)\b(things (just|always) happen(ing)? to me|I (was|am) just a (victim|bystander|passenger))\b`),
		"[REASONING — NARRATIVE] Locate even small choices; restore the author seat, not only the acted-upon role."},
	{sigRedemptionArc, regexp.MustCompile(`(?i)\b(even though .{0,40}I (learned|grew|found)|the (suffering|pain|struggle).{0,20}(taught me|made me stronger))\b`),
		"[REASONING — NARRATIVE] Affirm meaning-making already in progress without denying difficulty."},
}

// CollectReframes scans user text and returns at most one short inject (no retry).
func CollectReframes(userText string) string {
	text := strings.TrimSpace(userText)
	if text == "" {
		return ""
	}
	for _, p := range reframePatterns {
		if p.Re.MatchString(text) {
			return p.Inj
		}
	}
	return ""
}

// CollectRuminationInject detects low-velocity topic loops and returns a short prefix.
func CollectRuminationInject(messages []map[string]string) string {
	sig := NewRuminationTracker().Detect(messages)
	if !sig.Detected {
		return ""
	}
	if sig.Confidence >= 0.65 {
		return "[REASONING — LOOP] Some aspects may be fixed right now; focus on the next concrete movable step."
	}
	return "[REASONING — LOOP] This topic has recurred with low novelty; approach from a different angle rather than replaying the same frame."
}
