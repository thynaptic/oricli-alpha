package service

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/vdi"
)

// --- Pillar 53: Curiosity Daemon (Epistemic Foraging) ---
// Proactively fills gaps in the Working Memory Graph using VDI/Web.

type CuriosityEvent struct {
	TargetEntity string `json:"target_entity"`
	Action       string `json:"action"` // "searching", "scraping", "committing"
	Findings     string `json:"findings,omitempty"`
}

type CuriosityDaemon struct {
	Graph      *memory.WorkingMemoryGraph
	VDI        *vdi.Manager
	Gen        *GenerationService
	WSHub      interface {
		BroadcastEvent(eventType string, payload interface{})
	}
	Searcher *CollySearcher  // DDG fallback
	SearXNG  *SearXNGSearcher // primary sovereign search
	active bool
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
	ticker := time.NewTicker(15 * time.Minute) // Forage every 15 mins
	defer ticker.Stop()

	log.Println("[CuriosityDaemon] Epistemic loop engaged.")

	for {
		select {
		case <-ctx.Done():
			d.active = false
			return
		case <-ticker.C:
			// Only forage if system is "Idle" (Simple heuristic: no active inference for 5 mins)
			d.Forage(ctx)
		}
	}
}

func (d *CuriosityDaemon) Forage(ctx context.Context) {
	// 1. Find Gaps
	gaps := d.Graph.FindGaps()
	if len(gaps) == 0 {
		return
	}

	// 2. Select Target
	target := gaps[0]
	log.Printf("[CuriosityDaemon] Identifying knowledge gap: %s. Foraging...", target.Label)

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: target.Label,
			Action:       "searching",
		})
	}

	// 3. Web Foraging — priority: SearXNG (sovereign) → VDI browser → Colly/DDG fallback
	var rawText string
	var fetchErr error

	// Primary: local SearXNG instance (multi-engine aggregation, clean JSON)
	if d.SearXNG != nil {
		rawText, fetchErr = d.SearXNG.Search(target.Label + " facts summary")
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] SearXNG forage failed for %s: %v — trying VDI", target.Label, fetchErr)
		}
	}

	// Secondary: VDI headless browser (requires Chromium installed on host)
	if rawText == "" && d.VDI != nil && d.VDI.IsAvailable() {
		searchURL := fmt.Sprintf("https://duckduckgo.com/html/?q=%s+facts+summary",
			strings.ReplaceAll(target.Label, " ", "+"))
		_, fetchErr = d.VDI.Navigate(searchURL)
		if fetchErr == nil {
			rawText, fetchErr = d.VDI.Scrape()
		}
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] VDI forage failed for %s: %v — falling back to Colly", target.Label, fetchErr)
		}
	}

	// Last resort: Colly DDG scraper
	if rawText == "" {
		rawText, fetchErr = d.Searcher.Search(target.Label + " facts summary")
		if fetchErr != nil {
			log.Printf("[CuriosityDaemon] Colly forage also failed for %s: %v — skipping", target.Label, fetchErr)
			return
		}
	}

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: target.Label,
			Action:       "scraping",
		})
	}

	// 4. Fact Extraction
	prompt := fmt.Sprintf("Extract 3-5 key facts about '%s' from the following text. Format as a concise description suitable for a knowledge graph.\n\nTEXT: %s", target.Label, rawText)
	res, err := d.Gen.Generate(prompt, map[string]interface{}{
		"system": "Epistemic Curator",
		"model":  "ministral-3:3b",
	})
	if err != nil {
		log.Printf("[CuriosityDaemon] Fact extraction failed for %s: %v", target.Label, err)
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
			Action:       "committing",
			Findings:     factSummary,
		})
	}

	log.Printf("[CuriosityDaemon] Successfully filled gap for: %s", target.Label)
}
