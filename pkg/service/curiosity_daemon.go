package service

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/memory"
	"github.com/thynaptic/oricli-go/pkg/searchintent"
	"github.com/thynaptic/oricli-go/pkg/vdi"
)

// ─── Curiosity Daemon — Idle-Burst Epistemic Forager ─────────────────────────
//
// Phase 1 (always-on, zero-cost): Seeds accumulate from every conversation.
//   Each user message extracts topic seeds and queues them.
//
// Phase 2 (idle-only): When no requests for CURIOSITY_IDLE_MIN (default 20 min),
//   the daemon enters a research burst — burns through the seed queue, then fills
//   knowledge graph gaps. Stops immediately on any new request.
//
// This mirrors biological memory consolidation:
//   accumulate during the day → process during rest.

// CuriosityEvent is broadcast over WebSocket to surface foraging activity in the UI.
type CuriosityEvent struct {
	TargetEntity string `json:"target_entity"`
	Intent       string `json:"intent,omitempty"`
	Action       string `json:"action"` // "searching", "scraping", "committing", "session_start", "session_end"
	Findings     string `json:"findings,omitempty"`
}

// CuriositySeed is a topic extracted from a conversation that warrants research.
type CuriositySeed struct {
	Topic    string
	Source   string // e.g. "conversation", "graph_gap", "hypothesis"
	Priority float64
	AddedAt  time.Time
	Depth    int // hypothesis hop count; 0 = ground truth, ≥2 = capped
}

// CuriosityDaemon accumulates seeds from conversations and forages during idle periods.
type CuriosityDaemon struct {
	Graph   *memory.WorkingMemoryGraph
	VDI     *vdi.Manager
	Gen     *GenerationService
	WSHub   interface {
		BroadcastEvent(eventType string, payload interface{})
	}
	Searcher    *CollySearcher
	SearXNG     *SearXNGSearcher
	MemoryBank  *MemoryBank // PocketBase long-term memory (optional)
	Governor    *CostGovernor // optional spend guard for RunPod synthesis

	// RunPod synthesis: when true, forageTopic uses an LLM synthesis pass
	// instead of pure TF-IDF extraction — produces richer knowledge fragments.
	// Respects Governor budget. Env: WORLD_TRAVELER_USE_RUNPOD=true
	UseRunPodSynthesis bool

	// Seed queue — populated by conversation traffic, consumed during idle bursts
	seedMu   sync.Mutex
	seeds    []CuriositySeed
	seenKeys map[string]struct{} // dedup

	// Activity tracking — updated on every chat request
	lastActivity atomic.Int64 // UnixNano
	idleThreshold time.Duration

	// Interrupt channel — signals active burst to stop
	interruptCh chan struct{}
	interruptMu sync.Mutex

	active bool
}

func NewCuriosityDaemon(graph *memory.WorkingMemoryGraph, vdi *vdi.Manager, gen *GenerationService, hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) *CuriosityDaemon {
	idleMin := parseFloatEnv("CURIOSITY_IDLE_MIN", 20)
	d := &CuriosityDaemon{
		Graph:         graph,
		VDI:           vdi,
		Gen:           gen,
		WSHub:         hub,
		Searcher:      NewCollySearcher(),
		SearXNG:       NewSearXNGSearcher(),
		seenKeys:      make(map[string]struct{}),
		idleThreshold: time.Duration(idleMin) * time.Minute,
		interruptCh:   make(chan struct{}, 1),
	}
	d.lastActivity.Store(time.Now().UnixNano())
	return d
}

func (d *CuriosityDaemon) InjectWSHub(hub interface {
	BroadcastEvent(eventType string, payload interface{})
}) {
	d.WSHub = hub
}

// NotifyActivity must be called on every incoming chat request.
// It resets the idle timer and interrupts any active research burst.
func (d *CuriosityDaemon) NotifyActivity() {
	d.lastActivity.Store(time.Now().UnixNano())
	// Non-blocking send — burst goroutine drains this
	d.interruptMu.Lock()
	select {
	case d.interruptCh <- struct{}{}:
	default:
	}
	d.interruptMu.Unlock()
}

// AddSeed adds a topic to the research queue if not already seen.
// Called during message handling — must be O(1) and non-blocking.
func (d *CuriosityDaemon) AddSeed(topic, source string) {
	key := strings.ToLower(strings.TrimSpace(topic))
	if key == "" || len(key) < 4 {
		return
	}
	d.seedMu.Lock()
	defer d.seedMu.Unlock()
	if _, exists := d.seenKeys[key]; exists {
		return
	}
	d.seenKeys[key] = struct{}{}
	d.seeds = append(d.seeds, CuriositySeed{
		Topic:   topic,
		Source:  source,
		AddedAt: time.Now(),
	})
}

// AddSeedForce injects a topic into the research queue even if it was previously
// seen. Used by BenchmarkGapDetector so known weaknesses are re-studied on each
// benchmark cycle rather than silently dropped by the dedup filter.
func (d *CuriosityDaemon) AddSeedForce(topic, source string) {
	key := strings.ToLower(strings.TrimSpace(topic))
	if key == "" || len(key) < 4 {
		return
	}
	d.seedMu.Lock()
	defer d.seedMu.Unlock()
	// Remove from seenKeys so novelty cap doesn't apply on re-injection
	delete(d.seenKeys, key)
	d.seeds = append(d.seeds, CuriositySeed{
		Topic:   topic,
		Source:  source,
		AddedAt: time.Now(),
	})
}

// SeedFromMessage extracts curiosity seeds from a user message and queues them.
// Lightweight — no inference, just pattern matching.
func (d *CuriosityDaemon) SeedFromMessage(msg string) {
	for _, topic := range extractTopics(msg) {
		d.AddSeed(topic, "conversation")
	}
}

// Run starts the idle-detection loop. Blocks until ctx is cancelled.
func (d *CuriosityDaemon) Run(ctx context.Context) {
	d.active = true
	ticker := time.NewTicker(60 * time.Second) // check idle every minute
	defer ticker.Stop()

	log.Printf("[CuriosityDaemon] Idle-burst mode engaged — forages after %v of silence.", d.idleThreshold)

	for {
		select {
		case <-ctx.Done():
			d.active = false
			return
		case <-ticker.C:
			idleSince := time.Since(time.Unix(0, d.lastActivity.Load()))
			if idleSince >= d.idleThreshold {
				log.Printf("[CuriosityDaemon] System idle for %v — starting research burst", idleSince.Round(time.Second))
				d.runBurst(ctx)
			}
		}
	}
}

// runBurst processes the seed queue then fills knowledge graph gaps.
// Stops as soon as ctx is cancelled or activity is detected.
func (d *CuriosityDaemon) runBurst(ctx context.Context) {
	// Drain the interrupt channel before starting so we don't stop immediately
	select {
	case <-d.interruptCh:
	default:
	}

	// Pre-load known topics from PocketBase so we don't re-research them
	if d.MemoryBank != nil && d.MemoryBank.IsEnabled() {
		knownTopics, err := d.MemoryBank.QueryKnowledgeFragments(ctx, 500)
		if err == nil {
			d.seedMu.Lock()
			for _, t := range knownTopics {
				key := strings.ToLower(t)
				d.seenKeys[key] = struct{}{} // mark as already researched
			}
			d.seedMu.Unlock()
			if len(knownTopics) > 0 {
				log.Printf("[CuriosityDaemon] Pre-loaded %d known topics from PocketBase", len(knownTopics))
			}
		}
	}

	sessionStart := time.Now()
	processed := 0

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			Action: "session_start",
		})
	}

	// Phase A: Seed queue (conversation-derived, high signal)
	for {
		if d.interrupted(ctx) {
			log.Printf("[CuriosityDaemon] Burst interrupted after %d items (%v)", processed, time.Since(sessionStart).Round(time.Second))
			return
		}

		seed := d.popSeed()
		if seed == nil {
			break
		}
		d.forageTopic(ctx, seed.Topic, seed.Depth)
		processed++
	}

	// Phase B: Knowledge graph gaps (lower signal, fills structural holes)
	gaps := d.Graph.FindGaps()
	sort.Slice(gaps, func(i, j int) bool {
		return gaps[i].Importance*gaps[i].Uncertainty > gaps[j].Importance*gaps[j].Uncertainty
	})

	for _, gap := range gaps {
		if d.interrupted(ctx) {
			break
		}
		d.forageTopic(ctx, gap.Label, 0)
		processed++
		// Small pause between gap fills to avoid hammering search
		time.Sleep(3 * time.Second)
	}

	log.Printf("[CuriosityDaemon] Research burst complete — %d items in %v", processed, time.Since(sessionStart).Round(time.Second))

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			Action:   "session_end",
			Findings: fmt.Sprintf("%d items researched in %v", processed, time.Since(sessionStart).Round(time.Second)),
		})
	}
}

// interrupted returns true if activity was detected or ctx was cancelled.
func (d *CuriosityDaemon) interrupted(ctx context.Context) bool {
	select {
	case <-ctx.Done():
		return true
	case <-d.interruptCh:
		log.Printf("[CuriosityDaemon] Activity detected — pausing research burst")
		return true
	default:
		return false
	}
}

// popSeed removes and returns the highest-priority seed, or nil if queue is empty.
func (d *CuriosityDaemon) popSeed() *CuriositySeed {
	d.seedMu.Lock()
	defer d.seedMu.Unlock()
	if len(d.seeds) == 0 {
		return nil
	}
	seed := d.seeds[0]
	d.seeds = d.seeds[1:]
	return &seed
}

// forageTopic researches a single topic: search → scrape → extract → commit.
// depth tracks how many hypothesis hops removed from ground truth this topic is.
func (d *CuriosityDaemon) forageTopic(ctx context.Context, topic string, depth int) {
	// Novelty cap: skip topics we already have ≥3 knowledge fragments for.
	// This prevents the synthetic echo-chamber — Oricli must explore new territory.
	if d.MemoryBank != nil {
		count := d.MemoryBank.KnowledgeCount(ctx, topic)
		if count >= 3 {
			log.Printf("[CuriosityDaemon] skipping %q — already has %d fragments (novelty cap)", topic, count)
			return
		}
	}

	intent := searchintent.ClassifySearchIntent(topic)
	sq := searchintent.BuildSearchQuery(topic, intent)

	log.Printf("[CuriosityDaemon] Researching: %q (intent: %s)", topic, intent)

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: topic,
			Intent:       string(intent),
			Action:       "searching",
		})
	}

	// Web search — SearXNG + VDI deep-forage → Colly fallback
	var rawText string

	if d.SearXNG != nil {
		results, urlErr := d.SearXNG.SearchWithURLs(sq)
		if urlErr == nil && len(results) > 0 && d.VDI != nil && d.VDI.IsAvailable() {
			topN := results
			if len(topN) > 2 {
				topN = topN[:2]
			}
			type forage struct{ text string }
			forageCh := make(chan forage, len(topN))
			for _, r := range topN {
				url := r.URL
				go func() {
					// Prefer structured DOM extraction; falls back gracefully on error.
					pc, err := d.VDI.NavigateAndExtractDOM(url, 2500)
					if err != nil || pc == nil {
						forageCh <- forage{}
						return
					}
					forageCh <- forage{text: pc.FormatAsContext(2500)}
				}()
			}
			timer := time.NewTimer(5 * time.Second * time.Duration(len(topN)))
			var parts []string
			for i := 0; i < len(topN); i++ {
				select {
				case f := <-forageCh:
					if f.text != "" {
						parts = append(parts, f.text)
					}
				case <-timer.C:
				}
			}
			timer.Stop()
			if len(parts) > 0 {
				rawText = strings.Join(parts, "\n\n")
				if len(rawText) > 5000 {
					rawText = rawText[:5000] + "… [truncated]"
				}
			}
		}
		if rawText == "" {
			rawText, _ = d.SearXNG.SearchWithIntent(sq)
		}
	}
	if rawText == "" {
		var err error
		rawText, err = d.Searcher.Search(sq.FormattedQuery)
		if err != nil {
			log.Printf("[CuriosityDaemon] All search paths failed for %q: %v", topic, err)
			return
		}
	}

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: topic,
			Intent:       string(intent),
			Action:       "scraping",
		})
	}

	// ── Epistemic quality gate ────────────────────────────────────────────
	// Evaluate retrieved text before burning LLM tokens on extraction.
	// Bail early on clearly irrelevant or untrustworthy content.
	sourceURL := ""
	if d.SearXNG != nil {
		// Best-effort: use the topic query as a proxy; real URL unavailable
		// at this call site.  Wire a real URL when SearXNG results expose it.
		sourceURL = ""
	}
	epistemicResult := cognition.EpistemicFilter(topic, rawText, sourceURL)
	if !epistemicResult.Pass {
		log.Printf("[CuriosityDaemon] epistemic drop %q: %s", topic, epistemicResult.Reason)
		if d.WSHub != nil {
			d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
				TargetEntity: topic,
				Intent:       string(intent),
				Action:       "filtered",
				Findings:     epistemicResult.Reason,
			})
		}
		return
	}
	log.Printf("[CuriosityDaemon] epistemic pass %q (rel=%.2f trust=%.2f combined=%.2f)",
		topic, epistemicResult.Relevance, epistemicResult.Trust, epistemicResult.Combined)

	// Fact extraction — TF-IDF extractive summarizer (no LLM call).
	// Selects the highest-scoring sentences by cosine similarity to the
	// topic query, preserving document order. Deterministic, <5ms.
	factSummary := cognition.ExtractFacts(topic, rawText, intent)

	// ── RunPod synthesis upgrade (optional) ──────────────────────────────
	// When WORLD_TRAVELER_USE_RUNPOD=true and budget allows, replace the
	// TF-IDF summary with a richer LLM-synthesized knowledge fragment.
	// Falls back to TF-IDF output if synthesis fails or budget is exceeded.
	if d.UseRunPodSynthesis && d.Gen != nil {
		estimatedCost := EstimateRunPodCost(1)
		canSynth := d.Governor == nil || d.Governor.CanSpend(estimatedCost)
		if canSynth {
			synthPrompt := fmt.Sprintf(
				"You are a knowledge synthesis engine. Given raw search results about \"%s\", "+
					"produce a precise, factual 3-5 sentence summary that captures the most important "+
					"concepts, mechanisms, and relationships. Do not hallucinate. Stay grounded in the text.\n\n"+
					"Source text:\n%s\n\nSynthesis:",
				topic, rawText,
			)
			synthCtxTimeout, synthCancel := context.WithTimeout(ctx, 20*time.Second)
			_ = synthCtxTimeout
			res, err := d.Gen.Generate(synthPrompt, map[string]interface{}{
				"options": map[string]interface{}{
					"num_predict": 250,
					"num_ctx":     3072,
					"temperature": 0.2,
				},
			})
			synthCancel()
			if err == nil {
				if synthText, ok := res["text"].(string); ok && len(strings.TrimSpace(synthText)) > 30 {
					factSummary = strings.TrimSpace(synthText)
					if d.Governor != nil {
						d.Governor.RecordSpend(estimatedCost, "synthesis:"+topic)
					}
					log.Printf("[CuriosityDaemon] RunPod synthesis applied for %q", topic)
				}
			} else {
				log.Printf("[CuriosityDaemon] RunPod synthesis fallback (TF-IDF) for %q: %v", topic, err)
			}
		}
	}

	// Find or create entity in graph and commit
	gaps := d.Graph.FindGaps()
	for _, g := range gaps {
		if strings.EqualFold(g.Label, topic) {
			d.Graph.UpdateEntity(g.ID, 0.5, 0.5, 0.5, func(e *memory.Entity) {
				e.Description = factSummary
				e.Uncertainty = 0.2
			})
			break
		}
	}

	if d.WSHub != nil {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: topic,
			Intent:       string(intent),
			Action:       "committing",
			Findings:     factSummary,
		})
	}

	log.Printf("[CuriosityDaemon] Committed: %q", topic)

	// Persist finding to PocketBase long-term memory bank (async, non-blocking)
	if d.MemoryBank != nil {
		d.MemoryBank.WriteKnowledgeFragment(topic, string(intent), factSummary, 0.7)
	}

	// Hypothesis Engine: generate follow-up questions from what we just learned.
	// This closes the active inference loop — Oricli seeds her own future research.
	// Depth cap prevents infinite synthetic loops (max 2 hypothesis hops from ground truth).
	go d.generateHypotheses(ctx, topic, factSummary, depth)
}

// generateHypotheses asks the LLM what it still doesn't know after learning factSummary,
// then seeds those questions back into the research queue — closing the active inference loop.
func (d *CuriosityDaemon) generateHypotheses(ctx context.Context, topic, factSummary string, depth int) {
	// Hard cap: never generate hypotheses from hypothesis-derived knowledge
	if depth >= 2 {
		return
	}
	if d.Gen == nil {
		return
	}

	prompt := fmt.Sprintf(
		"You just learned the following about \"%s\":\n\n%s\n\n"+
			"Based only on what is stated above, list exactly 2 specific questions you cannot yet answer about this topic. "+
			"Each question must start with '?' on its own line. Be concrete and researchable. No preamble.",
		topic, factSummary,
	)

	genCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	res, err := d.Gen.Generate(prompt, map[string]interface{}{
		"model": d.Gen.DefaultModel, // use chat model to avoid Ollama eviction
		"options": map[string]interface{}{
			"num_predict": 150,
			"num_ctx":     2048,
			"temperature": 0.4,
		},
	})
	if err != nil {
		return
	}
	_ = genCtx

	text, _ := res["text"].(string)
	var hypotheses []string
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "?") {
			q := strings.TrimSpace(strings.TrimPrefix(line, "?"))
			if len(q) > 10 && len(q) < 200 {
				hypotheses = append(hypotheses, q)
			}
		}
	}
	if len(hypotheses) == 0 {
		return
	}

	added := 0
	for _, h := range hypotheses {
		if added >= 2 {
			break
		}
		// Novelty cap: don't add hypothesis if we already have fragments for it
		if d.MemoryBank != nil {
			count := d.MemoryBank.KnowledgeCount(ctx, h)
			if count >= 3 {
				continue
			}
		}
		d.seedMu.Lock()
		d.seeds = append(d.seeds, CuriositySeed{
			Topic:   h,
			Source:  "hypothesis",
			Depth:   depth + 1,
			AddedAt: time.Now(),
		})
		d.seedMu.Unlock()
		log.Printf("[CuriosityDaemon] Hypothesis seeded: %q (depth=%d)", h, depth+1)
		added++
	}

	if d.WSHub != nil && added > 0 {
		d.WSHub.BroadcastEvent("curiosity_sync", CuriosityEvent{
			TargetEntity: topic,
			Intent:       "hypothesis",
			Action:       "seeded",
			Findings:     strings.Join(hypotheses[:added], " | "),
		})
	}
}

// SeedQueueDepth returns the number of pending seeds (for diagnostics).
func (d *CuriosityDaemon) SeedQueueDepth() int {
	d.seedMu.Lock()
	defer d.seedMu.Unlock()
	return len(d.seeds)
}

// IdleSince returns how long the system has been idle.
func (d *CuriosityDaemon) IdleSince() time.Duration {
	return time.Since(time.Unix(0, d.lastActivity.Load()))
}

// ─── Topic extraction ─────────────────────────────────────────────────────────

var (
	reQuestion    = regexp.MustCompile(`(?i)(what|who|how|why|when|where|which|explain|tell me about|what is|what are)\s+([a-z][a-z0-9\s\-]{3,60})\??`)
	reNamedEntity = regexp.MustCompile(`\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b`)
	reTechTerm    = regexp.MustCompile(`\b([A-Z][a-zA-Z0-9]{2,}(?:\.[a-zA-Z]{2,})?)\b`) // CamelCase / acronyms
	reNumeric     = regexp.MustCompile(`^\d+(\.\d+)?$`)
)

// topicStopWords are common English words that carry no epistemic value as
// research topics. Any candidate topic that, when lowercased, matches one of
// these is silently dropped before it reaches the seed queue.
var topicStopWords = map[string]bool{
	// articles / determiners
	"the": true, "a": true, "an": true, "this": true, "that": true, "these": true, "those": true,
	// pronouns
	"i": true, "me": true, "my": true, "we": true, "us": true, "our": true,
	"you": true, "your": true, "he": true, "she": true, "it": true, "they": true, "them": true, "their": true,
	// common verbs
	"is": true, "are": true, "was": true, "were": true, "be": true, "been": true, "being": true,
	"have": true, "has": true, "had": true, "do": true, "does": true, "did": true,
	"will": true, "would": true, "could": true, "should": true, "may": true, "might": true, "can": true,
	"make": true, "made": true, "making": true, "want": true, "need": true, "get": true, "got": true,
	"go": true, "going": true, "come": true, "know": true, "think": true, "said": true, "say": true,
	"use": true, "used": true, "using": true, "look": true, "take": true, "see": true,
	// common adjectives / adverbs
	"full": true, "good": true, "great": true, "best": true, "new": true, "old": true, "big": true,
	"little": true, "small": true, "large": true, "long": true, "high": true, "low": true,
	"more": true, "most": true, "much": true, "many": true, "some": true, "any": true, "all": true,
	"also": true, "just": true, "only": true, "very": true, "well": true, "even": true, "back": true,
	"still": true, "same": true, "other": true, "such": true, "then": true, "than": true, "now": true,
	// prepositions / conjunctions
	"in": true, "on": true, "at": true, "to": true, "of": true, "for": true, "with": true,
	"from": true, "by": true, "as": true, "about": true, "into": true, "out": true,
	"up": true, "down": true, "over": true, "after": true, "before": true, "between": true,
	"and": true, "but": true, "or": true, "not": true, "no": true, "nor": true, "so": true,
	"if": true, "when": true, "where": true, "while": true, "because": true, "though": true,
	// generic UI / meta words that bleed in from chat context
	"page": true, "text": true, "here": true, "there": true, "what": true, "how": true,
	"which": true, "who": true, "help": true, "please": true, "thanks": true, "okay": true,
	"chat": true, "code": true, "file": true, "data": true, "type": true, "user": true,
	// ARC / benchmark prompt words
	"output": true, "input": true, "example": true, "respond": true, "response": true,
	"answer": true, "question": true, "task": true, "grid": true, "pattern": true,
	"color": true, "colour": true, "row": true, "column": true, "matrix": true,
}

// isWorthyTopic returns true only if a candidate topic is substantive enough
// to warrant autonomous research — not a stopword, not too short, not a bare number.
func isWorthyTopic(t string) bool {
	if len(t) < 6 || len(t) > 80 {
		return false
	}
	// Pure numbers / single-token numerics are not research topics
	if reNumeric.MatchString(t) {
		return false
	}
	return !topicStopWords[strings.ToLower(strings.TrimSpace(t))]
}

// extractTopics pulls candidate research topics from a user message.
// Deliberately lightweight — no inference, just pattern matching.
func extractTopics(msg string) []string {
	seen := make(map[string]struct{})
	var topics []string

	add := func(t string) {
		t = strings.TrimSpace(t)
		if !isWorthyTopic(t) {
			return
		}
		key := strings.ToLower(t)
		if _, ok := seen[key]; !ok {
			seen[key] = struct{}{}
			topics = append(topics, t)
		}
	}

	// Questions → extract the subject
	for _, m := range reQuestion.FindAllStringSubmatch(msg, 3) {
		if len(m) >= 3 {
			add(strings.TrimSpace(m[2]))
		}
	}

	// Named entities (multi-word capitalized)
	for _, m := range reNamedEntity.FindAllString(msg, 5) {
		add(m)
	}

	// CamelCase / tech acronyms
	for _, m := range reTechTerm.FindAllString(msg, 5) {
		add(m)
	}

	return topics
}




