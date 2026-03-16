package service

import (
	"math"
	"strings"
)

type SentimentResult struct {
	Sentiment  string  `json:"sentiment"`
	Polarity   float64 `json:"polarity"`
	Confidence float64 `json:"confidence"`
}

type NLPService struct {
	PositiveWords map[string]bool
	NegativeWords map[string]bool
}

func NewNLPService() *NLPService {
	return &NLPService{
		PositiveWords: map[string]bool{
			"good": true, "great": true, "excellent": true, "amazing": true,
			"love": true, "happy": true, "awesome": true, "nice": true,
		},
		NegativeWords: map[string]bool{
			"bad": true, "terrible": true, "awful": true, "hate": true,
			"sad": true, "angry": true, "dislike": true, "poor": true,
		},
	}
}

func (s *NLPService) AnalyzeSentiment(text string) SentimentResult {
	words := strings.Fields(strings.ToLower(text))
	pos, neg := 0, 0
	for _, w := range words {
		if s.PositiveWords[w] { pos++ }
		if s.NegativeWords[w] { neg++ }
	}

	polarity := 0.0
	sentiment := "neutral"
	if pos+neg > 0 {
		polarity = float64(pos-neg) / float64(pos+neg)
		if polarity > 0.1 {
			sentiment = "positive"
		} else if polarity < -0.1 {
			sentiment = "negative"
		}
	}

	return SentimentResult{
		Sentiment:  sentiment,
		Polarity:   polarity,
		Confidence: math.Abs(polarity),
	}
}

func (s *NLPService) CalculateSimilarity(text1, text2 string) float64 {
	w1 := strings.Fields(strings.ToLower(text1))
	w2 := strings.Fields(strings.ToLower(text2))
	
	m1 := make(map[string]int)
	m2 := make(map[string]int)
	allWords := make(map[string]bool)

	for _, w := range w1 { m1[w]++; allWords[w] = true }
	for _, w := range w2 { m2[w]++; allWords[w] = true }

	dot, norm1, norm2 := 0.0, 0.0, 0.0
	for w := range allWords {
		v1 := float64(m1[w])
		v2 := float64(m2[w])
		dot += v1 * v2
		norm1 += v1 * v1
		norm2 += v2 * v2
	}

	if norm1 == 0 || norm2 == 0 { return 0 }
	return dot / (math.Sqrt(norm1) * math.Sqrt(norm2))
}
