package cognition

import (
	"math"
	"regexp"
	"sort"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ---------------------------------------------------------------------------
// Extractive Summarizer — TF-IDF sentence scoring.
//
// Replaces the LLM extraction call in CuriosityDaemon.forageTopic().
// No model calls, no network I/O — pure deterministic text processing.
// Runs in <5ms on typical web snippets.
//
// Design:
//   - Split raw text into sentences
//   - Build a TF-IDF matrix over those sentences (topic query acts as the
//     reference "document" for IDF weighting)
//   - Score each sentence by its cosine similarity to the query token set
//   - Select top-K by score, preserving original document order
//   - Trim to a char budget so downstream storage stays predictable
// ---------------------------------------------------------------------------

const (
	summMaxSentences = 8
	summMaxChars     = 1500 // hard cap for knowledge graph entries
)

// SentenceLimit returns the intent-tuned sentence count.
func sentenceLimitForIntent(intent searchintent.SearchIntent) int {
	switch intent {
	case searchintent.IntentDefinition:
		return 3
	case searchintent.IntentFactual, searchintent.IntentEntity:
		return 5
	case searchintent.IntentTechnical, searchintent.IntentProcedural:
		return 6
	case searchintent.IntentCurrentEvents, searchintent.IntentComparative:
		return 7
	default:
		return 5
	}
}

// Stopwords — common English function words that carry no signal weight.
var summStopwords = map[string]bool{
	"a": true, "an": true, "the": true, "and": true, "or": true, "but": true,
	"in": true, "on": true, "at": true, "to": true, "for": true, "of": true,
	"with": true, "by": true, "from": true, "is": true, "are": true, "was": true,
	"were": true, "be": true, "been": true, "being": true, "have": true, "has": true,
	"had": true, "do": true, "does": true, "did": true, "will": true, "would": true,
	"could": true, "should": true, "may": true, "might": true, "that": true,
	"this": true, "these": true, "those": true, "it": true, "its": true,
	"i": true, "we": true, "you": true, "they": true, "he": true, "she": true,
	"as": true, "if": true, "then": true, "than": true, "so": true, "not": true,
	"no": true, "up": true, "out": true, "into": true, "about": true, "more": true,
}

var reSentenceSplit = regexp.MustCompile(`[.!?]+\s+|\n{2,}`)
var reToken         = regexp.MustCompile(`[a-z0-9]+`)

func summTokenize(text string) []string {
	raw := reToken.FindAllString(strings.ToLower(text), -1)
	out := raw[:0]
	for _, t := range raw {
		if len(t) >= 2 && !summStopwords[t] {
			out = append(out, t)
		}
	}
	return out
}

// termFreq returns a normalised TF map for the given token list.
func termFreq(tokens []string) map[string]float64 {
	counts := make(map[string]int, len(tokens))
	for _, t := range tokens {
		counts[t]++
	}
	tf := make(map[string]float64, len(counts))
	n := float64(max(len(tokens), 1))
	for t, c := range counts {
		tf[t] = float64(c) / n
	}
	return tf
}

// ExtractFacts is the public entry point called by CuriosityDaemon.
// It selects the most topically relevant sentences from rawText without
// any LLM calls. Returns a formatted string ready for graph storage.
func ExtractFacts(topic string, rawText string, intent searchintent.SearchIntent) string {
	sentences := splitSentences(rawText)
	if len(sentences) == 0 {
		return strings.TrimSpace(rawText[:min(len(rawText), summMaxChars)])
	}

	limit := sentenceLimitForIntent(intent)
	selected := rankSentences(topic, sentences, limit)
	if len(selected) == 0 {
		// Fallback: first N sentences by document order
		n := min(limit, len(sentences))
		selected = sentences[:n]
	}

	var b strings.Builder
	for i, s := range selected {
		b.WriteString(s)
		if i < len(selected)-1 {
			b.WriteString(" ")
		}
		if b.Len() >= summMaxChars {
			break
		}
	}
	result := strings.TrimSpace(b.String())
	if len(result) > summMaxChars {
		result = result[:summMaxChars]
	}
	return result
}

// splitSentences breaks rawText into non-empty sentence fragments.
func splitSentences(text string) []string {
	parts := reSentenceSplit.Split(text, -1)
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if len(p) >= 20 { // ignore fragments too short to be informative
			out = append(out, p)
		}
	}
	return out
}

// rankSentences scores each sentence by TF-IDF cosine similarity to the
// query topic, returns the top-limit sentences in original document order.
func rankSentences(topic string, sentences []string, limit int) []string {
	queryTokens := summTokenize(topic)
	if len(queryTokens) == 0 {
		return nil
	}

	// Build DF map across all sentences
	N := float64(len(sentences))
	df := make(map[string]int, 64)
	sentTokens := make([][]string, len(sentences))
	for i, s := range sentences {
		toks := summTokenize(s)
		sentTokens[i] = toks
		seen := make(map[string]bool, len(toks))
		for _, t := range toks {
			if !seen[t] {
				df[t]++
				seen[t] = true
			}
		}
	}

	// IDF for each query token
	queryIDF := make(map[string]float64, len(queryTokens))
	for _, t := range queryTokens {
		d := float64(df[t])
		queryIDF[t] = math.Log(1.0 + (N+1.0)/(d+1.0))
	}

	type scored struct {
		idx   int
		score float64
	}
	scores := make([]scored, len(sentences))
	for i, toks := range sentTokens {
		tf := termFreq(toks)
		var sim float64
		for _, qt := range queryTokens {
			idf := queryIDF[qt]
			sim += tf[qt] * idf
		}
		// Boost sentences that contain the topic verbatim
		if strings.Contains(strings.ToLower(sentences[i]), strings.ToLower(topic)) {
			sim *= 1.3
		}
		scores[i] = scored{i, sim}
	}

	// Sort by score descending
	sort.Slice(scores, func(a, b int) bool {
		return scores[a].score > scores[b].score
	})

	// Take top-limit, then restore document order
	k := min(limit, len(scores))
	top := scores[:k]
	// Filter zero-score entries
	filtered := top[:0]
	for _, s := range top {
		if s.score > 0 {
			filtered = append(filtered, s)
		}
	}
	if len(filtered) == 0 {
		return nil
	}
	sort.Slice(filtered, func(a, b int) bool {
		return filtered[a].idx < filtered[b].idx
	})

	out := make([]string, len(filtered))
	for i, s := range filtered {
		out[i] = sentences[s.idx]
	}
	return out
}


