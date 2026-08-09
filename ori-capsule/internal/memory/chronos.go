package memory

import (
	"math"
	"sync"
	"time"
)

type DecayCategory string

const (
	DecayContextual     DecayCategory = "contextual"
	DecayFactual        DecayCategory = "factual"
	DecayProcedural     DecayCategory = "procedural"
	DecayConstitutional DecayCategory = "constitutional"
)

func (c DecayCategory) halfLifeHours() float64 {
	switch c {
	case DecayContextual:
		return 72
	case DecayFactual:
		return 168
	case DecayProcedural:
		return 2160
	default:
		return 0
	}
}

// ChronosEntry is a temporal snapshot of one memory write (in-process).
type ChronosEntry struct {
	ID             string
	FragmentID     string
	Content        string
	Topic          string
	Source         string
	Category       DecayCategory
	BaseConfidence float64
	LearnedAt      time.Time
}

func (e *ChronosEntry) DecayedConfidence(now time.Time) float64 {
	hl := e.Category.halfLifeHours()
	if hl == 0 {
		return e.BaseConfidence
	}
	elapsed := now.Sub(e.LearnedAt).Hours()
	return e.BaseConfidence * math.Pow(0.5, elapsed/hl)
}

// ObserveInput is a flat write observation (no PB dependency).
type ObserveInput struct {
	ID         string
	Content    string
	Topic      string
	Source     string
	Importance float64
	Volatility string
	CreatedAt  time.Time
}

// ChronosIndex is a bounded in-memory temporal ring — no daemon loop.
type ChronosIndex struct {
	mu      sync.RWMutex
	entries []*ChronosEntry
	cap     int
	seq     uint64
}

func NewChronosIndex(cap int) *ChronosIndex {
	if cap <= 0 {
		cap = 2000
	}
	return &ChronosIndex{cap: cap}
}

func CategoryFromVolatility(volatility, source string, importance float64) DecayCategory {
	if (source == "identity" || source == "constitution") && importance >= 0.9 {
		return DecayConstitutional
	}
	switch volatility {
	case "ephemeral":
		return DecayContextual
	case "stable":
		if importance >= 0.8 {
			return DecayProcedural
		}
		return DecayFactual
	default:
		return DecayFactual
	}
}

func (idx *ChronosIndex) Observe(in ObserveInput) {
	t := in.CreatedAt
	if t.IsZero() {
		t = time.Now()
	}
	content := in.Content
	if len(content) > 500 {
		content = content[:500]
	}
	idx.mu.Lock()
	defer idx.mu.Unlock()
	idx.seq++
	e := &ChronosEntry{
		ID:             fmtChronosID(idx.seq),
		FragmentID:     in.ID,
		Content:        content,
		Topic:          in.Topic,
		Source:         in.Source,
		Category:       CategoryFromVolatility(in.Volatility, in.Source, in.Importance),
		BaseConfidence: in.Importance,
		LearnedAt:      t,
	}
	if len(idx.entries) >= idx.cap {
		idx.entries = idx.entries[1:]
	}
	idx.entries = append(idx.entries, e)
}

func (idx *ChronosIndex) Len() int {
	idx.mu.RLock()
	defer idx.mu.RUnlock()
	return len(idx.entries)
}

func (idx *ChronosIndex) Recent(n int) []*ChronosEntry {
	idx.mu.RLock()
	defer idx.mu.RUnlock()
	if n <= 0 || n > len(idx.entries) {
		n = len(idx.entries)
	}
	out := make([]*ChronosEntry, n)
	for i := 0; i < n; i++ {
		out[i] = idx.entries[len(idx.entries)-1-i]
	}
	return out
}

func fmtChronosID(seq uint64) string {
	return time.Now().UTC().Format("20060102T150405") + "-" + itoa(seq)
}

func itoa(u uint64) string {
	if u == 0 {
		return "0"
	}
	var b [20]byte
	i := len(b)
	for u > 0 {
		i--
		b[i] = byte('0' + u%10)
		u /= 10
	}
	return string(b[i:])
}
