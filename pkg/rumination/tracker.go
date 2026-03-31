package rumination

import (
	"strings"
	"unicode"
)

// RuminationTracker scans a message window for topic clusters with low epistemic velocity.
type RuminationTracker struct{}

// NewRuminationTracker returns a RuminationTracker.
func NewRuminationTracker() *RuminationTracker {
	return &RuminationTracker{}
}

// Detect scans messages for rumination patterns.
// messages is the conversation history (role/content maps).
// Returns a RuminationSignal.
func (t *RuminationTracker) Detect(messages []map[string]string) RuminationSignal {
	userMsgs := extractUserMessages(messages, WindowSize)
	if len(userMsgs) < OccurrenceThreshold {
		return RuminationSignal{}
	}

	clusters := make([]TopicCluster, len(userMsgs))
	for i, m := range userMsgs {
		clusters[i] = TopicCluster{
			Key:      fingerprint(m),
			MsgIndex: i,
			Snippet:  clip(m, 80),
		}
	}

	// Count cluster key frequencies
	freq := map[string][]int{}
	for i, c := range clusters {
		freq[c.Key] = append(freq[c.Key], i)
	}

	// Find most-recurring cluster
	bestKey := ""
	bestIdxs := []int{}
	for k, idxs := range freq {
		if len(idxs) > len(bestIdxs) {
			bestKey = k
			bestIdxs = idxs
		}
	}

	if len(bestIdxs) < OccurrenceThreshold {
		// Try loose cluster matching via jaccard similarity
		bestKey, bestIdxs = looseCluster(clusters)
	}

	if len(bestIdxs) < OccurrenceThreshold {
		return RuminationSignal{}
	}

	// Measure epistemic velocity across the cluster
	texts := make([]string, len(bestIdxs))
	for i, idx := range bestIdxs {
		texts[i] = userMsgs[idx]
	}
	avgVelocity := measureVelocity(texts)

	if avgVelocity >= VelocityThreshold {
		return RuminationSignal{TopicKey: bestKey, Occurrences: len(bestIdxs), AvgVelocity: avgVelocity}
	}

	confidence := confidenceScore(len(bestIdxs), avgVelocity)
	return RuminationSignal{
		Detected:    true,
		TopicKey:    bestKey,
		Occurrences: len(bestIdxs),
		AvgVelocity: avgVelocity,
		Confidence:  confidence,
		Snippet:     clusters[bestIdxs[0]].Snippet,
	}
}

// fingerprint produces a normalised bigram key from text.
func fingerprint(text string) string {
	words := tokenize(text)
	if len(words) == 0 {
		return ""
	}
	// Keep top 4 content words as key
	stop := stopWords()
	var content []string
	for _, w := range words {
		if !stop[w] {
			content = append(content, w)
		}
		if len(content) == 4 {
			break
		}
	}
	return strings.Join(content, "_")
}

// looseCluster finds the largest group of messages with pairwise jaccard ≥ 0.35.
func looseCluster(clusters []TopicCluster) (string, []int) {
	n := len(clusters)
	sets := make([]map[string]struct{}, n)
	for i, c := range clusters {
		sets[i] = wordSet(c.Key)
	}

	bestKey := ""
	bestGroup := []int{}
	for i := 0; i < n; i++ {
		group := []int{i}
		for j := i + 1; j < n; j++ {
			if jaccard(sets[i], sets[j]) >= 0.35 {
				group = append(group, j)
			}
		}
		if len(group) > len(bestGroup) {
			bestGroup = group
			bestKey = clusters[i].Key
		}
	}
	return bestKey, bestGroup
}

// measureVelocity computes the average pairwise novelty across a set of texts.
// Low value = high repetition = low epistemic progress.
func measureVelocity(texts []string) float64 {
	if len(texts) < 2 {
		return 1.0
	}
	sets := make([]map[string]struct{}, len(texts))
	for i, t := range texts {
		sets[i] = wordSet(strings.ToLower(t))
	}
	var total float64
	var count int
	for i := 0; i < len(sets); i++ {
		for j := i + 1; j < len(sets); j++ {
			// novelty = 1 - jaccard (high jaccard = low novelty)
			total += 1.0 - jaccard(sets[i], sets[j])
			count++
		}
	}
	if count == 0 {
		return 1.0
	}
	return total / float64(count)
}

func confidenceScore(occurrences int, avgVelocity float64) float64 {
	occScore := float64(occurrences-OccurrenceThreshold) / float64(WindowSize-OccurrenceThreshold)
	if occScore > 1 {
		occScore = 1
	}
	velScore := 1.0 - (avgVelocity / VelocityThreshold)
	if velScore < 0 {
		velScore = 0
	}
	return (occScore + velScore) / 2.0
}

func extractUserMessages(messages []map[string]string, n int) []string {
	var out []string
	for _, m := range messages {
		if m["role"] == "user" {
			out = append(out, m["content"])
		}
	}
	if len(out) > n {
		out = out[len(out)-n:]
	}
	return out
}

func tokenize(text string) []string {
	words := strings.FieldsFunc(strings.ToLower(text), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	return words
}

func wordSet(text string) map[string]struct{} {
	words := strings.Fields(text)
	s := make(map[string]struct{}, len(words))
	for _, w := range words {
		s[w] = struct{}{}
	}
	return s
}

func jaccard(a, b map[string]struct{}) float64 {
	if len(a) == 0 && len(b) == 0 {
		return 1.0
	}
	intersection := 0
	for k := range a {
		if _, ok := b[k]; ok {
			intersection++
		}
	}
	union := len(a) + len(b) - intersection
	if union == 0 {
		return 0
	}
	return float64(intersection) / float64(union)
}

func clip(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n]) + "…"
	}
	return s
}

func stopWords() map[string]bool {
	words := []string{
		"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
		"have", "has", "had", "do", "does", "did", "will", "would", "could",
		"should", "may", "might", "shall", "can", "to", "of", "in", "on",
		"at", "by", "for", "with", "about", "i", "you", "we", "it", "this",
		"that", "and", "or", "but", "not", "what", "how", "why", "when",
		"my", "your", "its", "me", "him", "her", "them", "us",
	}
	m := make(map[string]bool, len(words))
	for _, w := range words {
		m[w] = true
	}
	return m
}
