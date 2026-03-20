package cognition

import (
	"math/rand"
	"strings"
	"sync"
	"time"
)

// --- Pillar 15: Stochastic Inference (Markov Chain) ---
// Ported from Aurora's MarkovChainBuilder.swift.
// High-speed, zero-latency text generation for subconscious intent.

type Transition struct {
	NextWord    string
	Probability float64
}

type MarkovChain struct {
	// N-Gram Size -> [Prefix Key -> Transitions]
	NGrams map[int]map[string][]Transition
	mu     sync.RWMutex
}

func NewMarkovChain() *MarkovChain {
	return &MarkovChain{
		NGrams: make(map[int]map[string][]Transition),
	}
}

// Train processes a body of text and builds transition probabilities.
func (m *MarkovChain) Train(text string, maxNgramSize int) {
	m.mu.Lock()
	defer m.mu.Unlock()

	words := tokenizeMarkov(text)
	if len(words) < 2 {
		return
	}

	for size := 2; size <= maxNgramSize; size++ {
		if _, ok := m.NGrams[size]; !ok {
			m.NGrams[size] = make(map[string][]Transition)
		}

		counts := make(map[string]map[string]int)

		// Count occurrences
		for i := 0; i <= len(words)-size; i++ {
			prefix := strings.Join(words[i:i+size-1], " ")
			nextWord := words[i+size-1]

			if _, ok := counts[prefix]; !ok {
				counts[prefix] = make(map[string]int)
			}
			counts[prefix][nextWord]++
		}

		// Convert to probabilities
		for prefix, nextWords := range counts {
			total := 0
			for _, count := range nextWords {
				total += count
			}

			var transitions []Transition
			for nextWord, count := range nextWords {
				transitions = append(transitions, Transition{
					NextWord:    nextWord,
					Probability: float64(count) / float64(total),
				})
			}
			m.NGrams[size][prefix] = transitions
		}
	}
}

// Generate creates a phrase starting with a keyword seed.
func (m *MarkovChain) Generate(seed string, length int) string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	rng := rand.New(rand.NewSource(time.Now().UnixNano()))
	words := tokenizeMarkov(seed)
	if len(words) == 0 {
		return ""
	}

	for len(words) < length {
		nextWord := m.selectNextWord(words, rng)
		if nextWord == "" {
			break
		}
		words = append(words, nextWord)
		
		// Stop at punctuation boundary
		if strings.HasSuffix(nextWord, ".") || strings.HasSuffix(nextWord, "!") || strings.HasSuffix(nextWord, "?") {
			break
		}
	}

	// Capitalize first letter (basic)
	if len(words) > 0 {
		first := words[0]
		if len(first) > 0 {
			words[0] = strings.ToUpper(first[:1]) + first[1:]
		}
	}

	return strings.Join(words, " ")
}

// selectNextWord attempts to find the longest matching n-gram context.
func (m *MarkovChain) selectNextWord(context []string, rng *rand.Rand) string {
	// Try largest n-grams first (e.g., 4-gram -> 3-gram -> bigram)
	for size := 4; size >= 2; size-- {
		if len(context) >= size-1 {
			prefixWords := context[len(context)-(size-1):]
			prefix := strings.Join(prefixWords, " ")
			
			if transitions, ok := m.NGrams[size][prefix]; ok && len(transitions) > 0 {
				return selectFromTransitions(transitions, rng)
			}
		}
	}
	return ""
}

func selectFromTransitions(transitions []Transition, rng *rand.Rand) string {
	random := rng.Float64()
	cumulative := 0.0

	for _, t := range transitions {
		cumulative += t.Probability
		if random <= cumulative {
			return t.NextWord
		}
	}
	
	if len(transitions) > 0 {
		return transitions[0].NextWord
	}
	return ""
}

func tokenizeMarkov(text string) []string {
	lower := strings.ToLower(text)
	lower = strings.ReplaceAll(lower, "\n", " ")
	lower = strings.ReplaceAll(lower, "\t", " ")
	
	rawWords := strings.Fields(lower)
	var words []string

	for _, w := range rawWords {
		if len(w) == 0 {
			continue
		}
		// Check for punctuation at the end
		lastChar := w[len(w)-1:]
		if strings.Contains(".,!?;:", lastChar) {
			words = append(words, w[:len(w)-1])
			words = append(words, lastChar)
		} else {
			words = append(words, w)
		}
	}
	return words
}
