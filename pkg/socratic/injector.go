package socratic

import "fmt"

// ElenchusInjector surfaces hidden assumptions and restores epistemic humility pre-generation.
type ElenchusInjector struct{}

func NewElenchusInjector() *ElenchusInjector { return &ElenchusInjector{} }

var socraticInjections = map[SocraticSignalType]string{
	PseudoCertainty: `[SOCRATIC — PSEUDO-CERTAINTY DETECTED]
Socratic elenchus: a claim stated as "obvious" has typically not been examined — it has been inherited. Socrates' central insight was that the appearance of knowledge is more dangerous than acknowledged ignorance, because it forecloses inquiry.
Frame shift: treat "obviously" as a flag, not a fact. What would it look like to actually examine this claim? What evidence would count for or against it? Who benefits from it going unquestioned? Productive aporia — "I realize I don't actually know this" — is the beginning of genuine understanding, not a failure.`,

	UnexaminedAssumption: `[SOCRATIC — UNEXAMINED ASSUMPTION DETECTED]
Socrates: every argument rests on premises. If those premises are assumed rather than examined, the argument's conclusion inherits that instability. The elenchus does not attack conclusions — it interrogates the foundations.
Frame shift: identify the premise that is being treated as given. Ask: "What would need to be true for this to be correct? Is that actually true? How do I know?" The goal is not to destabilize — it is to rebuild on firmer ground. Examined assumptions can be held with confidence; unexamined ones are always vulnerable.`,

	BeggingTheQuestion: `[SOCRATIC — CIRCULAR REASONING DETECTED]
Socratic method: when the conclusion is embedded in the premise, no new ground has been covered — the argument is a closed loop that generates the feeling of proof without its substance.
Frame shift: locate where the conclusion is being smuggled in as a premise. Separate the claim from its justification. Ask: "What would convince someone who doesn't already agree with this? What is the actual independent evidence?" The strongest positions can withstand having their circularity removed.`,

	FalseDefinition: `[SOCRATIC — AMBIGUOUS DEFINITION DETECTED]
Socrates repeatedly showed that disputes dissolve when terms are defined clearly — and that many apparent agreements conceal deep definitional disagreements. Defining key terms is not pedantry; it is the precondition for genuine dialogue.
Frame shift: identify the key term being used. Ask: "What exactly does this word mean here? Are there multiple valid meanings? Is the argument relying on one meaning but evoking connotations of another?" Clarifying the definition often resolves the dispute — or reveals it was never really a dispute about facts, but about values.`,
}

var socraticPriority = []SocraticSignalType{PseudoCertainty, UnexaminedAssumption, BeggingTheQuestion, FalseDefinition}

func (e *ElenchusInjector) Inject(scan *SocraticScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[SocraticSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range socraticPriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", socraticInjections[p])
		}
	}
	return ""
}
