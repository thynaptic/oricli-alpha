package searchintent

import (
	"fmt"
	"regexp"
	"strings"
)

// ---------------------------------------------------------------------------
// SearchIntent — what kind of knowledge are we looking for?
// ---------------------------------------------------------------------------

// SearchIntent classifies the nature of a search query so the system can
// apply the right strategy, source hints, and SearXNG category.
type SearchIntent string

const (
	// IntentDefinition — looking up the meaning of a word or concept.
	// Signal: single abstract noun, "what is", "what does X mean", "define"
	// Strategy: "define {term}" → Wiktionary/Wikipedia, single pass
	IntentDefinition SearchIntent = "definition"

	// IntentFactual — retrieving a specific verifiable fact.
	// Signal: "when did", "who is", "how many", "what year", specific question
	// Strategy: direct question → encyclopedia sources, single pass
	IntentFactual SearchIntent = "factual"

	// IntentEntity — looking up a person, place, organisation, product, or brand.
	// Signal: title-cased proper noun or known name pattern
	// Strategy: "{name} Wikipedia" → Wikipedia-first
	IntentEntity SearchIntent = "entity"

	// IntentTopic — broad conceptual understanding, no specific answer expected.
	// Signal: multi-word concept without question markers
	// Strategy: multi-pass research, broad-then-narrow
	IntentTopic SearchIntent = "topic"

	// IntentTechnical — documentation, APIs, frameworks, code patterns.
	// Signal: camelCase, version numbers, ".js"/".py" suffixes, known tech keywords
	// Strategy: "{term} documentation" → official docs / GitHub / Stack Overflow
	IntentTechnical SearchIntent = "technical"

	// IntentCurrentEvents — news, recent happenings, time-sensitive info.
	// Signal: "latest", "recent", "news about", explicit year/month
	// Strategy: time_range=week, SearXNG news category
	IntentCurrentEvents SearchIntent = "current_events"

	// IntentComparative — comparing two or more things.
	// Signal: " vs ", "difference between", "compare X and Y"
	// Strategy: dual lookup then synthesis
	IntentComparative SearchIntent = "comparative"

	// IntentProcedural — step-by-step instructions or guides.
	// Signal: "how to", "steps to", "guide for", "tutorial"
	// Strategy: "{topic} step by step guide" → tutorials / docs
	IntentProcedural SearchIntent = "procedural"
)

// SearXNGCategory maps to SearXNG's ?categories= parameter.
type SearXNGCategory string

const (
	CategoryGeneral SearXNGCategory = "general"
	CategoryNews    SearXNGCategory = "news"
	CategoryScience SearXNGCategory = "science"
	CategoryIT      SearXNGCategory = "it"
	CategoryFiles   SearXNGCategory = "files"
)

// SearXNGTimeRange maps to SearXNG's ?time_range= parameter.
type SearXNGTimeRange string

const (
	TimeRangeNone  SearXNGTimeRange = ""
	TimeRangeDay   SearXNGTimeRange = "day"
	TimeRangeWeek  SearXNGTimeRange = "week"
	TimeRangeMonth SearXNGTimeRange = "month"
	TimeRangeYear  SearXNGTimeRange = "year"
)

// SearchQuery is the structured representation of what to search for and how.
type SearchQuery struct {
	// Intent classifies the search type.
	Intent SearchIntent
	// RawTopic is the original term or phrase before formatting.
	RawTopic string
	// FormattedQuery is the optimised query string to send to SearXNG.
	FormattedQuery string
	// SourceHints are preferred domains to prioritise in result ranking.
	SourceHints []string
	// MaxPasses controls how many iterative research passes to run.
	// 1 = single lookup; >1 = ResearchOrchestrator multi-pass.
	MaxPasses int
	// Category sets the SearXNG search category.
	Category SearXNGCategory
	// TimeRange sets the SearXNG time filter.
	TimeRange SearXNGTimeRange
}

// ---------------------------------------------------------------------------
// Heuristic classifier — pure regex, <1ms, no LLM
// ---------------------------------------------------------------------------

var (
	// Question-word prefixes that signal specific factual lookups
	reFactualPrefix = regexp.MustCompile(
		`(?i)^(when did|who is|who was|who are|how many|how much|what year|` +
			`where is|where was|which country|what is the capital|how old is|` +
			`what date|what time|how long did|how far is)`)

	// Definition signals
	reDefinitionPrefix = regexp.MustCompile(
		`(?i)^(what is|what are|what does|what do|define|definition of|meaning of|` +
			`explain what|what's a|what's an)\b`)

	// Single abstract noun (no spaces, not a proper noun) — likely definition
	reSingleAbstractNoun = regexp.MustCompile(`^[a-z][a-z\-]{2,30}$`)

	// Procedural signals
	reProceduralPrefix = regexp.MustCompile(
		`(?i)^(how to|how do i|how do you|steps to|step by step|guide (to|for)|` +
			`tutorial (on|for)|instructions (for|to)|walkthrough)`)

	// Comparative signals
	reComparative = regexp.MustCompile(
		`(?i)(\bvs\.?\b|\bversus\b|difference between|compare .+ and|.+ compared to)`)

	// Current events signals
	reCurrentEvents = regexp.MustCompile(
		`(?i)(latest|recent|news (about|on)|today'?s?|this week|this month|` +
			`current state of|right now|as of \d{4}|\b202[3-9]\b|\b20[3-9][0-9]\b)`)

	// Proper noun signals (Title Case, or ALL CAPS acronym)
	reProperNoun = regexp.MustCompile(`(^|\s)[A-Z][a-z]+(\s[A-Z][a-z]+)+`)
	reTechnical = regexp.MustCompile(
		`(?i)(` +
			`\.(js|ts|py|go|rs|rb|sh|yaml|json|toml|proto)\b|` + // file extensions
			`\b(api|sdk|cli|orm|rpc|grpc|rest|graphql|oauth|jwt|llm|rag|gpu|cpu|ram|` +
			`docker|kubernetes|k8s|terraform|ansible|nginx|caddy|postgres|mysql|redis|` +
			`mongodb|kafka|rabbitmq|elasticsearch|opensearch|neo4j|lmdb|chromem|` +
			`pytorch|tensorflow|jax|cuda|triton|vllm|ollama|huggingface|langchain|` +
			`react|vue|svelte|nextjs|fastapi|gin|fiber|flask|django|rails|spring)\b|` +
			`v\d+(\.\d+)?` + // version numbers like v2.0 or v16
			`)`)

	// CamelCase/PascalCase compound names — company names, product names
	// e.g. OpenAI, DeepMind, YouTube, GitHub, PostgreSQL
	reCamelCase = regexp.MustCompile(`^[A-Z][a-z]+[A-Z][a-zA-Z0-9]*$`)
	reAcronym    = regexp.MustCompile(`\b[A-Z]{2,6}\b`)
)

// ClassifySearchIntent analyses a topic string and returns the most appropriate
// SearchIntent. This is a pure heuristic — no LLM, must complete in <1ms.
func ClassifySearchIntent(topic string) SearchIntent {
	t := strings.TrimSpace(topic)
	lower := strings.ToLower(t)

	// Comparative check first — explicit signal
	if reComparative.MatchString(lower) {
		return IntentComparative
	}

	// Procedural
	if reProceduralPrefix.MatchString(lower) {
		return IntentProcedural
	}

	// Current events
	if reCurrentEvents.MatchString(lower) {
		return IntentCurrentEvents
	}

	// Factual (specific question)
	if reFactualPrefix.MatchString(lower) {
		return IntentFactual
	}

	// Definition
	if reDefinitionPrefix.MatchString(lower) {
		return IntentDefinition
	}

	// Technical
	if reTechnical.MatchString(t) {
		return IntentTechnical
	}

	// Single lowercase word with no uppercase = definition lookup
	// (t == lower ensures it's not a proper noun like "OpenAI")
	words := strings.Fields(lower)
	if len(words) == 1 && reSingleAbstractNoun.MatchString(lower) && t == lower {
		return IntentDefinition
	}

	// Entity: primarily a proper name — first word must start with uppercase.
	// Also catches CamelCase compound names (OpenAI, DeepMind, GitHub).
	// Long descriptive phrases starting with lowercase are topics, not entities.
	firstIsUpper := len(t) > 0 && t[0] >= 'A' && t[0] <= 'Z'
	if firstIsUpper {
		if reProperNoun.MatchString(t) ||
			(reAcronym.MatchString(t) && len(words) <= 3) ||
			(len(words) == 1 && reCamelCase.MatchString(t)) {
			return IntentEntity
		}
	}

	// Default: treat as a broad topic
	return IntentTopic
}

// ---------------------------------------------------------------------------
// Query builder — maps intent to optimised query + metadata
// ---------------------------------------------------------------------------

var sourceHints = map[SearchIntent][]string{
	IntentDefinition:    {"wikipedia.org", "merriam-webster.com", "dictionary.com"},
	IntentFactual:       {"wikipedia.org", "britannica.com"},
	IntentEntity:        {"wikipedia.org", "britannica.com"},
	IntentTopic:         {"wikipedia.org", "britannica.com", "coursera.org"},
	IntentTechnical:     {"github.com", "stackoverflow.com", "pkg.go.dev", "docs.python.org", "developer.mozilla.org"},
	IntentCurrentEvents: {"reuters.com", "bbc.com", "apnews.com", "techcrunch.com"},
	IntentComparative:   {"wikipedia.org", "github.com", "stackoverflow.com"},
	IntentProcedural:    {"stackoverflow.com", "github.com", "docs.python.org", "developer.mozilla.org"},
}

var categoryMap = map[SearchIntent]SearXNGCategory{
	IntentDefinition:    CategoryGeneral,
	IntentFactual:       CategoryGeneral,
	IntentEntity:        CategoryGeneral,
	IntentTopic:         CategoryGeneral,
	IntentTechnical:     CategoryIT,
	IntentCurrentEvents: CategoryNews,
	IntentComparative:   CategoryGeneral,
	IntentProcedural:    CategoryGeneral,
}

var maxPassesMap = map[SearchIntent]int{
	IntentDefinition:    1,
	IntentFactual:       1,
	IntentEntity:        1,
	IntentTopic:         3,
	IntentTechnical:     2,
	IntentCurrentEvents: 1,
	IntentComparative:   2,
	IntentProcedural:    2,
}

// BuildSearchQuery returns a fully-formed SearchQuery ready for SearXNGSearcher.
func BuildSearchQuery(topic string, intent SearchIntent) SearchQuery {
	t := strings.TrimSpace(topic)
	var formatted string
	var timeRange SearXNGTimeRange

	switch intent {
	case IntentDefinition:
		formatted = fmt.Sprintf("define %s meaning", t)
	case IntentFactual:
		formatted = t // already a question
	case IntentEntity:
		formatted = fmt.Sprintf("%s Wikipedia", t)
	case IntentTopic:
		formatted = t
	case IntentTechnical:
		formatted = fmt.Sprintf("%s documentation reference", t)
	case IntentCurrentEvents:
		formatted = t
		timeRange = TimeRangeWeek
	case IntentComparative:
		formatted = t
	case IntentProcedural:
		formatted = fmt.Sprintf("how to %s step by step guide", stripHowTo(t))
	default:
		formatted = t
	}

	hints := sourceHints[intent]
	if hints == nil {
		hints = []string{}
	}

	return SearchQuery{
		Intent:         intent,
		RawTopic:       t,
		FormattedQuery: formatted,
		SourceHints:    hints,
		MaxPasses:      maxPassesMap[intent],
		Category:       categoryMap[intent],
		TimeRange:      timeRange,
	}
}

// stripHowTo removes leading "how to" / "how do i" prefixes before re-adding
// them in the canonical form, so we don't get "how to how to X".
func stripHowTo(s string) string {
	lower := strings.ToLower(s)
	prefixes := []string{"how to ", "how do i ", "how do you ", "steps to "}
	for _, p := range prefixes {
		if strings.HasPrefix(lower, p) {
			return s[len(p):]
		}
	}
	return s
}
