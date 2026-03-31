package interference

import (
	"fmt"
	"strings"
)

// ConflictSurfacer generates a pre-generation injection that names the conflict
// and instructs the model to resolve it explicitly rather than blending.
type ConflictSurfacer struct{}

func NewConflictSurfacer() *ConflictSurfacer { return &ConflictSurfacer{} }

// Surface builds a system-level instruction to name and resolve detected conflicts.
func (cs *ConflictSurfacer) Surface(r InterferenceReading) string {
	if !r.Detected || len(r.Conflicts) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("COGNITIVE INTERFERENCE DETECTED (Stroop Effect): ")
	sb.WriteString("The conversation contains contradictory instructions. ")
	sb.WriteString("Do NOT blend them — blending produces incoherent output. ")
	sb.WriteString("Instead: acknowledge the contradiction, state your chosen resolution, then proceed.\n\n")

	sb.WriteString("Detected conflicts:\n")
	for i, c := range r.Conflicts {
		sb.WriteString(fmt.Sprintf(
			"  %d. [%s] '%s'  ←→  '%s'\n",
			i+1, c.Type, c.StatementA, c.StatementB,
		))
	}
	sb.WriteString("\nInstruction: Pick the most recent or most specific constraint as authoritative. State your choice before answering.")
	return sb.String()
}
