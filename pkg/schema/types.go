// Package schema implements Phase 31: Schema Therapy (Young) + TFP Splitting Detector (Kernberg).
// Schema Therapy: detects the active emotional mode (Abandoned Child, Angry Child,
// Punitive Parent, Detached Protector) and responds with mode-appropriate framing.
// TFP Splitting: detects binary idealization/devaluation ("all good" vs "all bad")
// and injects an integration prompt before generation.
package schema

// SchemaMode identifies the active emotional mode from Schema Therapy.
type SchemaMode string

const (
	ModeAbandonedChild  SchemaMode = "abandoned_child"   // catastrophic abandonment/rejection fears
	ModeAngryChild      SchemaMode = "angry_child"        // rage at injustice, feeling unheard
	ModePunitiveParent  SchemaMode = "punitive_parent"    // harsh inner critic, self-blame
	ModeDetachedProtect SchemaMode = "detached_protector" // emotional numbness, shutdown
	ModeHealthyAdult    SchemaMode = "healthy_adult"      // balanced, integrated — goal state
	ModeNone            SchemaMode = "none"
)

// SplittingType classifies the TFP splitting pattern.
type SplittingType string

const (
	Idealization  SplittingType = "idealization"   // "X is perfect/amazing/the best"
	Devaluation   SplittingType = "devaluation"    // "X is terrible/worthless/evil"
	SplitDual     SplittingType = "split_dual"     // both present in same message
	SplittingNone SplittingType = "none"
)

// SchemaScan is the combined result of mode + splitting detection.
type SchemaScan struct {
	Mode          SchemaMode
	ModeMatches   []string
	Splitting     SplittingType
	SplitMatches  []string
	AnyDetected   bool
}
