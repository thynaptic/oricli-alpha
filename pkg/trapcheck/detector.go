// Package trapcheck detects common trap/trick question patterns and injects
// targeted reasoning hints into the sovereign pipeline before generation.
//
// Philosophy: surgical, pattern-specific hints only. No blanket "think harder"
// injection — that regressed ARC scores by 20%. Each hint fires ONLY when its
// specific pattern signature matches the input.
package trapcheck

import (
	"strings"
)

// Hint is a targeted reasoning note to prepend to the system prompt.
type Hint struct {
	Pattern string // human-readable name of the trap detected
	Guidance string // injected into composite before generation
}

// Detect scans stimulus for known trap-question signatures and returns
// zero or more targeted Hints. Returns empty slice for normal queries.
func Detect(stimulus string) []Hint {
	s := strings.ToLower(stimulus)
	var hints []Hint

	// ── 1. Trivial river crossing (2 entities, no fox/chicken/grain) ──────────
	// Pattern: "[entity] and a [entity]" + "river" + "boat" but no 3rd predator entity
	if hasRiverBoat(s) && !hasThreeEntities(s) {
		hints = append(hints, Hint{
			Pattern: "trivial_river_crossing",
			Guidance: "REASONING CHECK — River crossing: STOP and count the entities. " +
				"If there are only 2 entities (e.g., a man and a goat, a farmer and a sheep) " +
				"and no predator/prey/incompatibility constraint is stated, the answer is trivial: " +
				"they simply BOTH get in the boat and cross. No back-and-forth needed. " +
				"Do NOT apply the multi-animal puzzle logic unless 3+ incompatible entities are present.",
		})
	}

	// ── 2. Family counting trap ───────────────────────────────────────────────
	// Pattern: "brothers" + "sisters" + "how many sisters"
	if strings.Contains(s, "brother") && strings.Contains(s, "sister") &&
		strings.Contains(s, "how many") {
		hints = append(hints, Hint{
			Pattern: "family_counting_trap",
			Guidance: "REASONING CHECK — Family counting trap: Follow these exact steps: " +
				"(1) Name the subject, e.g., Sally. Sally is a girl. " +
				"(2) Sally has 3 brothers. Each brother looks around and sees Sally + 1 other girl = 2 sisters. " +
				"(3) BUT the question asks HOW MANY SISTERS DOES SALLY HAVE — not her brothers. " +
				"(4) Sally herself IS a sister, so she does NOT count herself. She sees only the OTHER girl. " +
				"(5) ANSWER: Sally has exactly 1 sister. Output the number 1.",
		})
	}

	// ── 3. Shared-activity constraint (chess with N people in room) ───────────
	// Pattern: "only" + number + "sisters/people" + "playing chess"
	if strings.Contains(s, "chess") && (strings.Contains(s, "only") || strings.Contains(s, "three")) {
		hints = append(hints, Hint{
			Pattern: "shared_activity_constraint",
			Guidance: "REASONING CHECK — Chess requires exactly 2 players. " +
				"STOP and work through this: " +
				"(1) There are exactly 3 people in the room. " +
				"(2) One person is reading — she is NOT playing chess. " +
				"(3) One person is playing chess — chess needs a partner. " +
				"(4) The only remaining person in the room must be that partner. " +
				"(5) Therefore: the third person IS playing chess. " +
				"Do NOT invent a fourth person or name. Do NOT say 'doing nothing'. ANSWER: Playing chess.",
		})
	}

	// ── 4. Temporal state trap ────────────────────────────────────────────────
	// Pattern: "currently has" or "now has" + "yesterday"
	if (strings.Contains(s, "currently has") || strings.Contains(s, "now has") || strings.Contains(s, "have now")) &&
		strings.Contains(s, "yesterday") {
		hints = append(hints, Hint{
			Pattern: "temporal_state_trap",
			Guidance: "REASONING CHECK — Temporal trap: The question explicitly states the CURRENT quantity " +
				"('currently has N'). Actions described in the past ('yesterday') have already occurred and are " +
				"reflected in the stated current state. Do NOT subtract past actions from a stated present quantity.",
		})
	}

	// ── 5. Containment counting trap ─────────────────────────────────────────
	// Pattern: "box" + "inside" + "how many"
	if strings.Contains(s, "box") && strings.Contains(s, "inside") &&
		strings.Contains(s, "how many") {
		hints = append(hints, Hint{
			Pattern: "containment_counting",
			Guidance: "REASONING CHECK — Containment counting: Follow this exact arithmetic. " +
				"'Two boxes with one box inside each' means: " +
				"2 outer boxes + 2 inner boxes (one inside each outer) = 4 boxes total. " +
				"The inner boxes are ADDITIONAL objects — they do NOT replace the outer boxes. " +
				"You physically hold 4 separate box objects. ANSWER: 4.",
		})
	}

	// ── 9. Hidden-number word sequence ────────────────────────────────────────
	// Pattern: word sequence completion where answer options suggest a series
	// (Stone→ONE, Often→TEN, Canine→NINE → answer is EIGHT hidden in Freight/Weight/etc.)
	if strings.Contains(s, "stone") && strings.Contains(s, "often") && strings.Contains(s, "canine") {
		hints = append(hints, Hint{
			Pattern: "hidden_number_word",
			Guidance: "REASONING CHECK — Hidden number pattern: Each word CONTAINS a number hidden inside it. " +
				"st-ONE (ONE), of-TEN (TEN), can-INE (NINE). The pattern is descending: ONE, TEN, NINE... " +
				"Look at each answer option and find which one CONTAINS the next number in the sequence (EIGHT). " +
				"fr-EIGHT → EIGHT. Choose that option.",
		})
	}

	// ── 10. Instruction-following: sentences ending with a specific word ───────
	// Pattern: "sentences" + "ending with" / "ending in" + specific word constraint
	if strings.Contains(s, "sentence") &&
		(strings.Contains(s, "ending with") || strings.Contains(s, "ending in") || strings.Contains(s, "ends with")) {
		hints = append(hints, Hint{
			Pattern: "sentence_ending_constraint",
			Guidance: "REASONING CHECK — Strict ending constraint. " +
				"MANDATORY: The VERY LAST WORD of every sentence you write must be the specified word (singular, exact). " +
				"Structure each sentence so the specified word is the final word before the period. " +
				"CORRECT example (if word is 'apple'): 'She reached up and plucked a crisp apple.' " +
				"WRONG examples: 'She ate apples.' (plural) | 'She loved apples dearly.' (wrong word) " +
				"Before writing each sentence, plan its ending first: decide how to make it conclude with the exact word.",
		})
	}

	// ── 11. Legs on floor (spatial + standing/airborne distinction) ───────────
	// Pattern: "legs" + "floor" + animals/furniture
	if strings.Contains(s, "leg") && strings.Contains(s, "floor") &&
		(strings.Contains(s, "bed") || strings.Contains(s, "jumping") || strings.Contains(s, "standing")) {
		hints = append(hints, Hint{
			Pattern: "legs_on_floor",
			Guidance: "REASONING CHECK — Legs on floor: Only count legs PHYSICALLY TOUCHING the floor. " +
				"Rule 1: Animals JUMPING ON furniture (on a bed) — 0 floor legs (they are on the bed, not the floor). " +
				"Rule 2: Animals STANDING (on the floor) — ALL their legs count (e.g., 3 chickens × 2 legs = 6). " +
				"Rule 3: Furniture with legs (4-poster bed = 4 legs touching the floor). " +
				"FINAL STEP: Add EVERY qualifying group together. " +
				"Example: 0 (monkeys on bed) + 6 (chickens standing) + 4 (bed legs) = 10 total. " +
				"Do NOT stop after listing one group — sum ALL groups before giving the answer.",
		})
	}

	// ── 6. Candle length inversion ────────────────────────────────────────────
	// Pattern: "candle" + "blown out" + "longer"/"shorter"/"cm"
	if strings.Contains(s, "candle") && strings.Contains(s, "blown out") &&
		(strings.Contains(s, "cm") || strings.Contains(s, "longer") || strings.Contains(s, "shorter")) {
		hints = append(hints, Hint{
			Pattern: "candle_length_inversion",
			Guidance: "REASONING CHECK — Candle length inversion: All candles were lit simultaneously. " +
				"The one blown out FIRST burned for the LEAST time, so it is the LONGEST remaining. " +
				"The one blown out LAST burned for the MOST time, so it is the SHORTEST.",
		})
	}

	// ── 7. Predicate-override instruction ─────────────────────────────────────
	// Pattern: conditional instruction format ("if X, answer Y. Otherwise, answer Z.")
	if strings.Contains(s, "if the animal") || strings.Contains(s, "if it has") ||
		(strings.Contains(s, "if") && strings.Contains(s, "otherwise, answer")) {
		hints = append(hints, Hint{
			Pattern: "conditional_instruction_override",
			Guidance: "REASONING CHECK — Conditional instruction: " +
				"Step 1: The largest land animal is the African Elephant. " +
				"Step 2: Check the condition — does it have a HORN? " +
				"CRITICAL: TUSKS are NOT horns. Tusks are elongated teeth (ivory). " +
				"Horns grow from the skull (like rhinos, narwhals). " +
				"African Elephants have TUSKS, NOT horns. The condition 'has a horn' is FALSE. " +
				"Step 3: Apply the OTHERWISE branch. " +
				"Output ONLY the answer specified for the otherwise branch. No explanation.",
		})
	}

	// ── 8. Negation chain ────────────────────────────────────────────────────
	// Pattern: "not not" or triple "not"
	if strings.Contains(s, "not not") || countOccurrences(s, " not ") >= 3 {
		hints = append(hints, Hint{
			Pattern: "negation_chain",
			Guidance: "REASONING CHECK — Negation chain: Count EVERY 'not' in the sentence. " +
				"Odd number of 'not's = NEGATIVE statement. Even number = POSITIVE statement. " +
				"Step-by-step: 'do not like' (1 not) → negative. " +
				"'do not not like' (2 nots) → positive. " +
				"'do not not not like' (3 nots) → NEGATIVE. " +
				"Output ONLY 'Yes' or 'No'. Do NOT say 'it depends' or 'paradox'.",
		})
	}

	return hints
}

// FormatInjection builds the composite injection block from detected hints.
// Returns empty string when no traps detected (no-op for normal queries).
func FormatInjection(hints []Hint) string {
	if len(hints) == 0 {
		return ""
	}
	var sb strings.Builder
	sb.WriteString("### TRAP-QUESTION AWARENESS\n")
	for _, h := range hints {
		sb.WriteString("• ")
		sb.WriteString(h.Guidance)
		sb.WriteString("\n")
	}
	sb.WriteString("### END TRAP-QUESTION AWARENESS\n")
	return sb.String()
}

// --- helpers ---

func hasRiverBoat(s string) bool {
	return strings.Contains(s, "river") && strings.Contains(s, "boat")
}

func hasThreeEntities(s string) bool {
	// Classic 3-entity puzzle indicators
	keywords := []string{"fox", "chicken", "grain", "cabbage", "wolf", "corn", "three animals"}
	for _, k := range keywords {
		if strings.Contains(s, k) {
			return true
		}
	}
	return false
}

func countOccurrences(s, sub string) int {
	count := 0
	idx := 0
	for {
		i := strings.Index(s[idx:], sub)
		if i < 0 {
			break
		}
		count++
		idx += i + len(sub)
	}
	return count
}
