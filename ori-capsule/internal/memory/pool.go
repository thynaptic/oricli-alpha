package memory

import (
	"sync"
	"time"
)

// TouchPool mirrors oracle session pool — last-used bookkeeping only.
type TouchPool struct {
	ttl time.Duration
	m   sync.Map
}

func NewTouchPool(ttl time.Duration) *TouchPool {
	if ttl <= 0 {
		ttl = 30 * time.Minute
	}
	p := &TouchPool{ttl: ttl}
	go p.reapLoop()
	return p
}

func (p *TouchPool) Touch(sessionID string) {
	if sessionID == "" {
		return
	}
	p.m.Store(sessionID, time.Now())
}

func (p *TouchPool) reapLoop() {
	t := time.NewTicker(5 * time.Minute)
	defer t.Stop()
	for range t.C {
		cutoff := time.Now().Add(-p.ttl)
		p.m.Range(func(k, v any) bool {
			if v.(time.Time).Before(cutoff) {
				p.m.Delete(k)
			}
			return true
		})
	}
}
