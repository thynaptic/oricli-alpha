package cognition

import (
	"net/url"
	"regexp"
	"strings"
)

// FilterResult holds the epistemic evaluation of a piece of retrieved text.
type FilterResult struct {
	// Pass is true when the text cleared the quality threshold.
	Pass bool
	// Relevance is the keyword-overlap score (0–1).
	Relevance float64
	// Trust is the source credibility score (0–1).
	Trust float64
	// Combined is the weighted composite score used for the pass decision.
	Combined float64
	// Reason is a short human-readable explanation of the decision.
	Reason string
}

// EpistemicFilter evaluates arbitrary retrieved text against a topic and
// source URL. It applies three layers:
//   - Relevance: keyword overlap between topic tokens and text tokens
//   - Source trust: domain-tier heuristic based on known credibility tiers
//   - Combined threshold gate (default 0.30)
//
// The result embeds scores for observability; use FilterResult.Pass to decide
// whether to include the text in downstream processing.
func EpistemicFilter(topic, text, rawURL string) FilterResult {
	rel := scoreRelevance(topic, text)
	trust := scoreSourceTrust(rawURL)
	combined := 0.55*rel + 0.45*trust

	const threshold = 0.30
	pass := combined >= threshold
	reason := buildReason(pass, rel, trust, combined)
	return FilterResult{
		Pass:      pass,
		Relevance: rel,
		Trust:     trust,
		Combined:  combined,
		Reason:    reason,
	}
}

// scoreRelevance returns 0–1 based on Jaccard-style overlap of query tokens
// against text tokens. Stopwords and short tokens (<3 chars) are excluded.
// Matches in the first 300 chars (headline/lead) are weighted 2×.
func scoreRelevance(topic, text string) float64 {
	qTokens := epistemicTokenize(topic)
	if len(qTokens) == 0 {
		return 0.5 // no signal
	}
	lead := text
	if len(lead) > 300 {
		lead = lead[:300]
	}
	leadTokens := epistemicTokenize(lead)
	bodyTokens := epistemicTokenize(text)

	leadSet := make(map[string]bool, len(leadTokens))
	for _, t := range leadTokens {
		leadSet[t] = true
	}
	bodySet := make(map[string]bool, len(bodyTokens))
	for _, t := range bodyTokens {
		bodySet[t] = true
	}

	var score float64
	for _, qt := range qTokens {
		if leadSet[qt] {
			score += 2.0
		} else if bodySet[qt] {
			score += 1.0
		}
	}
	// Normalise: best case = every query token hits the lead (2× each)
	max := float64(len(qTokens)) * 2.0
	if max == 0 {
		return 0.5
	}
	r := score / max
	if r > 1.0 {
		r = 1.0
	}
	return r
}

// scoreSourceTrust returns a credibility score 0–1 based on the domain of url.
// Tiers:
//
//	Tier 1 (0.95): academic/government/primary journals
//	Tier 2 (0.80): reputable news, reference, major tech docs
//	TLD bonus  :  .edu → 0.88, .gov → 0.90, .org → 0.65
//	Default    :  0.50
//	Tier 0     :  known low-trust / content farms → 0.20
func scoreSourceTrust(rawURL string) float64 {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return 0.40
	}
	host := strings.ToLower(parsed.Hostname())
	host = strings.TrimPrefix(host, "www.")

	if score, ok := domainTrustLookup(host); ok {
		return score
	}
	// TLD fallback
	switch {
	case strings.HasSuffix(host, ".edu"):
		return 0.88
	case strings.HasSuffix(host, ".gov"):
		return 0.90
	case strings.HasSuffix(host, ".org"):
		return 0.65
	default:
		return 0.50
	}
}

func domainTrustLookup(host string) (float64, bool) {
	for domain, score := range trustTiers {
		if host == domain || strings.HasSuffix(host, "."+domain) {
			return score, true
		}
	}
	return 0, false
}

func buildReason(pass bool, rel, trust, combined float64) string {
	verdict := "PASS"
	if !pass {
		verdict = "DROP"
	}
	var parts []string
	if rel < 0.25 {
		parts = append(parts, "low relevance")
	}
	if trust < 0.40 {
		parts = append(parts, "low-trust source")
	}
	if combined >= 0.55 {
		parts = append(parts, "strong combined score")
	}
	detail := strings.Join(parts, "; ")
	if detail == "" {
		detail = "adequate scores"
	}
	return verdict + " — " + detail
}

// epistemicTokenize lowercases, splits on non-alphanumeric runs, removes stopwords
// and tokens shorter than 3 characters. Returns unique tokens.
func epistemicTokenize(s string) []string {
	raw := reSplit.Split(strings.ToLower(s), -1)
	seen := make(map[string]bool, len(raw))
	out := make([]string, 0, len(raw))
	for _, t := range raw {
		if len(t) < 3 || stopWords[t] || seen[t] {
			continue
		}
		seen[t] = true
		out = append(out, t)
	}
	return out
}

var reSplit = regexp.MustCompile(`[^a-z0-9]+`)

var stopWords = map[string]bool{
	"the": true, "and": true, "for": true, "are": true, "but": true,
	"not": true, "you": true, "all": true, "can": true, "has": true,
	"her": true, "was": true, "one": true, "our": true, "out": true,
	"she": true, "day": true, "get": true, "his": true, "how": true,
	"its": true, "may": true, "now": true, "own": true, "say": true,
	"too": true, "use": true, "way": true, "who": true, "did": true,
	"doe": true, "had": true, "him": true, "let": true, "old": true,
	"see": true, "two": true, "why": true, "ask": true, "men": true,
	"ran": true, "set": true, "sit": true, "try": true, "yet": true,
	"ago": true, "air": true, "bit": true, "boy": true, "car": true,
	"cut": true, "eat": true, "few": true, "got": true, "hit": true,
	"hot": true, "job": true, "law": true, "lay": true, "led": true,
	"lot": true, "man": true, "met": true, "nor": true, "pay": true,
	"per": true, "put": true, "run": true, "tax": true, "top": true,
	"war": true, "win": true, "won": true, "yes": true,
}

// trustTiers maps canonical domain → trust score (0–1).
var trustTiers = map[string]float64{
	// ── Tier 1: academic, primary journals, government ──────────────────────
	"arxiv.org":                   0.95,
	"pubmed.ncbi.nlm.nih.gov":     0.95,
	"ncbi.nlm.nih.gov":            0.95,
	"nature.com":                  0.95,
	"science.org":                 0.95,
	"cell.com":                    0.95,
	"thelancet.com":               0.95,
	"bmj.com":                     0.95,
	"nejm.org":                    0.95,
	"ieee.org":                    0.95,
	"acm.org":                     0.95,
	"who.int":                     0.95,
	"cdc.gov":                     0.95,
	"nih.gov":                     0.95,
	"gov.uk":                      0.92,
	"europa.eu":                   0.90,
	"mit.edu":                     0.92,
	"stanford.edu":                0.92,
	"harvard.edu":                 0.92,
	"cambridge.org":               0.92,
	"oxfordacademic.com":          0.90,
	"link.springer.com":           0.90,
	"sciencedirect.com":           0.90,
	"jstor.org":                   0.90,

	// ── Tier 2: reputable news, reference, tech documentation ───────────────
	"reuters.com":           0.82,
	"apnews.com":            0.82,
	"bbc.com":               0.80,
	"bbc.co.uk":             0.80,
	"theguardian.com":       0.78,
	"nytimes.com":           0.78,
	"wsj.com":               0.78,
	"economist.com":         0.80,
	"ft.com":                0.78,
	"bloomberg.com":         0.78,
	"npr.org":               0.80,
	"pbs.org":               0.78,
	"wikipedia.org":         0.75,
	"britannica.com":        0.80,
	"github.com":            0.78,
	"stackoverflow.com":     0.72,
	"docs.python.org":       0.85,
	"developer.mozilla.org": 0.85,
	"techcrunch.com":        0.68,
	"wired.com":             0.70,
	"arstechnica.com":       0.72,
	"theverge.com":          0.65,

	// ── Tier 0: known low-quality / content farms ───────────────────────────
	"buzzfeed.com":      0.20,
	"dailymail.co.uk":   0.22,
	"thesun.co.uk":      0.22,
	"infowars.com":      0.05,
	"naturalnews.com":   0.08,
	"breitbart.com":     0.15,
	"ask.com":           0.20,
	"answers.com":       0.20,
	"quora.com":         0.28,
}
