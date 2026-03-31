package logotherapy

import "fmt"

// MeaningReconstructor injects Frankl-informed meaning-reconstruction frames pre-generation.
type MeaningReconstructor struct{}

func NewMeaningReconstructor() *MeaningReconstructor { return &MeaningReconstructor{} }

var meaningInjections = map[MeaningSignalType]string{
	ExistentialVacuum: `[LOGOTHERAPY — EXISTENTIAL VACUUM DETECTED]
Frankl's Logotherapy: the absence of felt meaning is not proof that meaning is absent — it is a signal that the will-to-meaning has not yet found its object. The vacuum is not the end state; it is the opening condition.
Frame shift: the question is not "does life have meaning?" but "what does this specific situation demand of me?" Meaning is not found by looking inward — it is discovered by responding to what the world is asking. Attend to the particular, not the general.`,

	MeaningCollapse: `[LOGOTHERAPY — MEANING COLLAPSE DETECTED]
Frankl's Tragic Triad: suffering, guilt, and mortality are not obstacles to meaning — they are the conditions within which the deepest meaning is forged. The prior source of meaning may have collapsed, but the capacity for meaning has not.
Frame shift: the collapse of one meaning structure creates the space for a more resilient one. The person who has rebuilt meaning after its collapse holds it more deliberately than the person who never lost it. Ask: what new form is this situation calling for?`,

	FrustrationOfMeaning: `[LOGOTHERAPY — FRUSTRATION OF MEANING DETECTED]
Frankl: meaning cannot be manufactured through introspection alone. It is found through (1) creative values — what we give to the world; (2) experiential values — what we receive through encounter, truth, beauty, love; (3) attitudinal values — the stance we take toward unavoidable suffering.
Frame shift: when direct search for meaning fails, move to the attitudinal axis. How is this person choosing to orient themselves toward what cannot be changed? That orientation IS a meaning source, independent of outcome.`,

	WillToMeaning: `[LOGOTHERAPY — WILL TO MEANING ACTIVE]
Frankl: the will-to-meaning is already awake and searching. This is the primary motivational force — it does not need to be created, only directed.
Frame shift: the question "what is the meaning?" is often too abstract. Reframe to: "what is this particular moment, this specific situation, asking of you right now?" Meaning is found in response, not in contemplation. Engage the concrete task in front of the person.`,
}

// Reconstruct returns the highest-priority injection for the scan.
// Priority: ExistentialVacuum > MeaningCollapse > FrustrationOfMeaning > WillToMeaning
var meaningPriority = []MeaningSignalType{ExistentialVacuum, MeaningCollapse, FrustrationOfMeaning, WillToMeaning}

func (r *MeaningReconstructor) Reconstruct(scan *MeaningScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[MeaningSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range meaningPriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", meaningInjections[p])
		}
	}
	return ""
}
