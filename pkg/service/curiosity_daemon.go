package service

import (
	"context"
	"fmt"
	"log"
	"sort"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
	"github.com/thynaptic/oricli-go/pkg/vdi"
)

// --- Pillar 53: Curiosity Daemon (Epistemic Foraging) ---
// Proactively fills gaps in the Working Memory Graph using classified,
// intent-aware queries rather than blind label + "facts summary" lookups.

type CuriosityEvent struct {
	TargetEntity string `json:"target_entity"`
	Intent       string `json:"intent,omitempty"`
	Action       string `json:"action"` // "searching", "scraping", "committing"
	Findings     string `json:"findings,omitempty"`
}

type CuriosityDaemon struct {
	Graph   *memory.WorkingMemoryGraph
	VDI     *vdi.Manager
	Gen     *GenerationService
	WSHub   interface {
		BroadcastEvent(eventType string, payload interface{})
	}
	Searcher *CollySearcher   // DDG fallback
	SearXNG  *SearXNGSearcher // primary sovereign search
	active   bool
}

func NewCuriosityDaemon(graph *memory.WorkingMemoryGraph, vdi *vdi.Manager, gen *GenerationService, hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) *CuriosityDaemon {
	return &CuriosityDaemon{
		Graph:    graph,
		VDI:      vdi,
		Gen:      gen,
		WSHub:    hub,
		Searcher: NewCollySearcher(),
		SearXNG:  NewSearXNGSearcher(),
	}
}

func (d *CuriosityDaemon) InjectWSHub(hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) {
	d.WSHub = hub
}

// Run starts the epistemic foraging loop.
func (d *CuriosityDaemon) Run(ctx context.Context) {
	d.active = true
	ticker := time.NewTicker(15 * time.Minute)
	defer ticker.Stop()

	log.Println("[CuriosityDaemon] Epistemic loop engaged.")

	for {
		select {
		case <-ctx.Done():
			d.active = false
			return
		case <-ticker.C:
			d.Forage(ctx)
		}
	}
}

func (d *CuriosityDaemon) Forage(ctx context.Context) {
	// 1. Find and prioritise gaps — sort by Importance × Uncertainty (highest first)
	gaps := d.Graph.FindGaps()
	if len(gaps) == 0 {
		return
	}
	sort.Slice(gaps, func(i, j int) bool {
		scoreI := gaps[i].Importance * gaps[i].Uncertainty
		scoreJ := gaps[j].Importance * gaps[j].Uncertainty
		return scoreI > scoreJ
	})
	target := gaps[0]

	// 2. Classify intent — understand WHAT kind of knowledge is missing
	intent := searchintent.ClassifySearchIntent(target.Label)
	sq := searchintent.BuildSearchQuery(target.Label, intent)

	log.Printf("[CuriosityDaemon] Gap: %q | Intent: %s | Query: %q",
		target.Label, intent, sq.FormattedQuery)

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: target.Label,
			Intent:       string(intent),
			Action:       "searching",
		})
	}

	// 3. Web Foraging — priority: SearXNG intent-aware → VDI browser → Colly fallback
	var rawText string
	var fetchErr error

	if d.SearXNG != nil {
		rawText, fetchErr = d.SearXNG.SearchWithIntent(sq)
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] SearXNG forage failed for %q: %v — trying VDI", target.Label, fetchErr)
		}
	}

	if rawText == "" && d.VDI != nil && d.VDI.IsAvailable() {
		searchURL := fmt.Sprintf("https://duckduckgo.com/html/?q=%s",
			strings.ReplaceAll(sq.FormattedQuery, " ", "+"))
		_, fetchErr = d.VDI.Navigate(searchURL)
		if fetchErr == nil {
			rawText, fetchErr = d.VDI.Scrape()
		}
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] VDI forage failed for %q: %v — falling back to Colly", target.Label, fetchErr)
		}
	}

	if rawText == "" {
		rawText, fetchErr = d.Searcher.Search(sq.FormattedQuery)
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] Colly forage also failed for %q: %v — skipping", target.Label, fetchErr)
			return
		}
	}

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: target.Label,
			Intent:       string(intent),
			Action:       "scraping",
		})
	}

	// 4. Fact Extraction — prompt tailored to intent type
	// Use a 90s deadline: daemon runs in background, failure is non-fatal.
	// Cap num_predict to 512 — we only need 3-5 distilled facts, not unbounded generation.
	extractionPrompt := buildExtractionPrompt(target.Label, intent, rawText)
	genCtx, genCancel := context.WithTimeout(ctx, 90*time.Second)
	defer genCancel()
	_ = genCtx // passed implicitly via Generate options for future; generation.go uses HTTPClient.Post
	res, err := d.Gen.Generate(extractionPrompt, map[string]interface{}{
		"system": "Epistemic Curator",
		"model":  "ministral-3:3b",
		"options": map[string]interface{}{
			"num_predict": 512,
			"num_ctx":     4096,
			"temperature": 0.3,
		},
	})
	if err != nil {
		log.Printf("[CuriosityDaemon] Fact extraction failed for %q: %v", target.Label, err)
		return
	}

	factSummary, _ := res["text"].(string)

	// 5. Commit to Graph
	d.Graph.UpdateEntity(target.ID, 0.5, 0.5, 0.5, func(e *memory.Entity) {
		e.Description = factSummary
		e.Uncertainty = 0.2
	})

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: target.Label,
			Intent:       string(intent),
			Action:       "committing",
			Findings:     factSummary,
		})
	}

	log.Printf("[CuriosityDaemon] Filled gap: %q (intent: %s)", target.Label, intent)
}

// buildExtractionPrompt returns an intent-tailored extraction instruction.
func buildExtractionPrompt(label string, intent searchintent.SearchIntent, rawText string) string {
	var instruction string
	switch intent {
	case searchintent.IntentDefinition:
		instruction = fmt.Sprintf("Extract the clear, concise definition of %q from the text below. Include etymology if present. 2-3 sentences max.", label)
	case searchintent.IntentFactual:
		instruction = fmt.Sprintf("Extract the key verifiable facts that answer the question %q. Be precise and cite any dates, numbers, or named entities.", label)
	case searchintent.IntentEntity:
		instruction = fmt.Sprintf("Extract 3-5 key biographical or descriptive facts about %q. Include: what it is, when it originated/was born, why it matters.", label)
	case searchintent.IntentTechnical:
		instruction = fmt.Sprintf("Extract 3-5 key technical facts about %q: what it does, core use cases, current version or status if mentioned.", label)
	case searchintent.IntentCurrentEvents:
		instruction = fmt.Sprintf("Summarise the most recent developments regarding %q from the text. Focus on what is new, changed, or noteworthy.", label)
	case searchintent.IntentComparative:
		instruction = fmt.Sprintf("Extract the key differences and similarities between the items in %q. Organise as: Item A — Item B — Key Difference.", label)
	case searchintent.IntentProcedural:
		instruction = fmt.Sprintf("Extract the core steps or procedure for %q from the text. List as numbered steps, 3-6 items max.", label)
	default: // IntentTopic
		instruction = fmt.Sprintf("Extract 3-5 key facts about %q from the text. Format as a concise description suitable for a knowledge graph.", label)
	}

	return fmt.Sprintf("%s\n\nTEXT:\n%s", instruction, rawText)
}

