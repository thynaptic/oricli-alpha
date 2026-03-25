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
// source URL. Scoring weights and thresholds are driven by the loaded
// Source Constitution (data/source_constitution.json), with safe hardcoded
// fallbacks when the file is absent.
func EpistemicFilter(topic, text, rawURL string) FilterResult {
	c := LoadConstitution()

	// Hard-block check — constitution absolute veto
	host := hostOf(rawURL)
	if c.IsHardBlocked(host, rawURL) {
		return FilterResult{Pass: false, Reason: "hard-blocked by constitution"}
	}

	// Ingestion rules — length + paywall/block signals
	if ok, reason := c.PassesIngestionRules("", text, rawURL); !ok {
		return FilterResult{Pass: false, Reason: "ingestion rule: " + reason}
	}

	relW, trustW := c.Weights()
	rel   := scoreRelevance(topic, text)
	trust := scoreSourceTrust(host, c)
	combined := relW*rel + trustW*trust

	pass := combined >= c.Threshold()
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

// scoreSourceTrust returns a credibility score 0–1 for a hostname,
// driven entirely by the loaded Source Constitution.
func scoreSourceTrust(host string, c *Constitution) float64 {
	if host == "" {
		return 0.40
	}
	return c.DomainScore(host)
}

// hostOf extracts and normalises the hostname from a raw URL string.
func hostOf(rawURL string) string {
	if rawURL == "" {
		return ""
	}
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return ""
	}
	host := strings.ToLower(parsed.Hostname())
	return strings.TrimPrefix(host, "www.")
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

