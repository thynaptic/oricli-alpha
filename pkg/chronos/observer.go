package chronos

import "time"

// Observer wraps a ChronosIndex and provides the WriteHook.
type Observer struct {
idx *ChronosIndex
}

// NewObserver creates an Observer backed by the given ChronosIndex.
func NewObserver(idx *ChronosIndex) *Observer {
return &Observer{idx: idx}
}

// Observe records an ObserveInput into the underlying ChronosIndex.
// Call this from the MemoryBank WriteHook in main.go:
//
//mb.WriteHook = func(frag service.MemoryFragment) {
//    obs.Observe(chronos.ObserveInput{
//        ID: frag.ID, Content: frag.Content, Topic: frag.Topic,
//        Source: frag.Source, Importance: frag.Importance,
//        Volatility: string(frag.Volatility), CreatedAt: frag.CreatedAt,
//    })
//}
func (o *Observer) Observe(in ObserveInput) {
o.idx.Observe(in)
}

// StaleContext builds a short warning string listing high-importance stale
// topics. Returns "" when nothing is stale — safe to prepend unconditionally.
func StaleContext(idx *ChronosIndex) string {
if idx == nil || idx.Len() == 0 {
return ""
}
now := time.Now()
all := idx.All()
var stale []string
for _, e := range all {
if e.IsStale(now, StaleThreshold) && e.BaseConfidence >= 0.6 {
topic := e.Topic
if topic == "" {
topic = e.Content
if len(topic) > 60 {
topic = topic[:60] + "…"
}
}
stale = append(stale, topic)
if len(stale) >= 5 {
break
}
}
}
if len(stale) == 0 {
return ""
}
out := "[⚠ Temporal Note — stale knowledge (>80% confidence decayed): "
for i, t := range stale {
if i > 0 {
out += ", "
}
out += t
}
return out + ". Qualify your response accordingly.]\n\n"
}
