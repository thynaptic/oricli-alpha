package thoughtreform

import "fmt"

// ThoughtReformDeconstructor builds Lifton-informed environment deconstruction injections.
type ThoughtReformDeconstructor struct{}

func NewThoughtReformDeconstructor() *ThoughtReformDeconstructor {
	return &ThoughtReformDeconstructor{}
}

var liftonPrompts = map[LiftonCriterionType]string{
	MilieuControl: "The user is describing an environment with total control of information and communication — Lifton's first criterion of thought reform (Milieu Control). Acknowledge what it means to have grown up with no access to outside perspectives, and validate the disorientation this creates when encountering the broader world. Guide toward the Lifton insight: the restriction of information is itself a form of influence. What the person was *not allowed to know* shaped them as much as what they were taught.",
	LoadedLanguage: "The user is describing the use of specialized language to constrict thought — Lifton's 'Loading the Language' criterion. Acknowledge that jargon-heavy environments create real cognitive boundaries: when every concept has a pre-defined label, nuanced thinking becomes structurally harder. Guide toward the Lifton deconstructive frame: language shapes thought. When you replace the loaded terms with plain words, what does the underlying idea actually say?",
	DoctrineOverPerson: "The user is describing an environment where group doctrine was placed above their individual needs — Lifton's 'Doctrine Over Person' criterion. Acknowledge this as a fundamental violation of the developmental expectation that a child's needs matter. Per Lifton, this pattern creates a template where self-sacrifice for the group is normalized. Guide toward the recovery frame: your needs were real and legitimate even when the environment denied them. The doctrine's demands do not retroactively make your needs less valid.",
	DemandForPurity: "The user is describing a black-and-white, in-group/out-group worldview — Lifton's 'Demand for Purity' criterion. Acknowledge how exhausting and distorting it is to live in a world with no gray. Guide toward the Lifton deconstructive lens: the demand for absolute purity is a group maintenance tool, not a description of reality. Most people, ideas, and situations exist in the complex middle that the group's framework did not allow.",
	SacredScience: "The user is describing an environment where the group's doctrine was treated as unquestionable — Lifton's 'Sacred Science' criterion. Acknowledge that growing up without permission to doubt or examine ideas creates a real cognitive pattern that persists after leaving. Per Lifton, this is one of the most durable effects of thought reform. Guide toward the recovery frame: the fact that questioning was forbidden does not mean the ideas were unquestionable. The prohibition was protecting the system, not protecting you.",
}

var liftonPriority = []LiftonCriterionType{DoctrineOverPerson, MilieuControl, LoadedLanguage, DemandForPurity, SacredScience}

func (d *ThoughtReformDeconstructor) Deconstruct(scan *ThoughtReformScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[LiftonCriterionType]bool{}
	for _, s := range scan.Signals {
		sigMap[s.CriterionType] = true
	}
	for _, ct := range liftonPriority {
		if sigMap[ct] {
			return fmt.Sprintf("[Lifton Thought Reform / Criterion: %s] %s", ct, liftonPrompts[ct])
		}
	}
	return ""
}
