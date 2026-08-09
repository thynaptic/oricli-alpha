package safety

import "log"

// Pipeline bundles the structural safety gates used on every capsule chat turn.
// No VPS daemons — pure in-process checks.
type Pipeline struct {
	Sentinel     *Sentinel
	Adversarial  *AdversarialAuditor
	Disclosure   *DisclosureGuard
	WebGuard     *WebInjectionGuard
	Canary       *CanarySystem
	MultiTurn    *MultiTurnAnalyzer
	Suspicion    *SuspicionTracker
	Canvas       *CanvasGuard
	RagGuard     *RagContentGuard
	Refinement   *RefinementEngine
	SCAI         *SCAIAuditor
	Constitution *Constitution
	RateLimiter  *RateLimiter
	Support      *SupportEngine
}

func NewPipeline() *Pipeline {
	constitution := NewSovereignConstitution()
	return &Pipeline{
		Sentinel:     NewSentinel(),
		Adversarial:  NewAdversarialAuditor(),
		Disclosure:   NewDisclosureGuard(),
		WebGuard:     NewWebInjectionGuard(),
		Canary:       NewCanarySystem(),
		MultiTurn:    &MultiTurnAnalyzer{},
		Suspicion:    NewSuspicionTracker(),
		Canvas:       NewCanvasGuard(),
		RagGuard:     NewRagContentGuard(),
		Refinement:   NewRefinementEngine(),
		SCAI:         NewSCAIAuditor(constitution, ""),
		Constitution: constitution,
		RateLimiter:  NewRateLimiter(),
		Support:      NewSupportEngine(),
	}
}

// CheckInput runs pre-inference gates on a single user message.
// Order: Normalize → Sentinel → Adversarial → DID → Web Injection → Canary
func (p *Pipeline) CheckInput(input string, codeContext bool) (blocked bool, refusal string) {
	normalized := NormalizeInput(input)

	if res := p.Sentinel.CheckInput(normalized); res.Detected {
		log.Printf("[Safety:Input] Sentinel blocked [%s / %s]", res.Type, res.Severity)
		return true, res.Replacement
	}
	if res := p.Adversarial.AuditInput(normalized, nil, codeContext); res.Detected {
		log.Printf("[Safety:Input] Adversarial blocked [%s %.2f]", res.Type, res.Confidence)
		return true, res.Refusal
	}
	if res := p.Disclosure.ScanInput(normalized); res.Detected {
		log.Printf("[Safety:Input] DID blocked [%s / %s]", res.Category, res.Severity)
		return true, res.Refusal
	}
	if res := p.WebGuard.ScanInput(normalized); res.Detected {
		log.Printf("[Safety:Input] WebGuard blocked [%s / %s]", res.Category, res.Severity)
		return true, res.Refusal
	}
	if res := p.Canary.ScanInput(normalized); res.Blocked {
		log.Printf("[Safety:Input] Canary trip [%s]", res.AlertType)
		return true, res.Message
	}
	return false, ""
}

// CheckInputWithHistory adds multi-turn + suspicion tracking, then CheckInput.
func (p *Pipeline) CheckInputWithHistory(messages []ChatTurn, sessionKey string, codeContext bool) (bool, string) {
	if len(messages) >= 2 {
		if mt := p.MultiTurn.AnalyzeHistory(messages); mt.Detected {
			log.Printf("[Safety:MultiTurn] Blocked [%s]: %s", mt.Pattern, mt.Reason)
			p.Suspicion.RecordBlock(sessionKey, "high")
			return true, mt.Refusal
		}
	}
	lastMsg := ""
	for i := len(messages) - 1; i >= 0; i-- {
		if messages[i].Role == "user" {
			lastMsg = messages[i].Content
			break
		}
	}
	if lastMsg == "" {
		return false, ""
	}
	if p.Suspicion.IsHardBlocked(sessionKey) {
		return true, "This session has been temporarily restricted due to repeated safety violations."
	}
	blocked, refusal := p.CheckInput(lastMsg, codeContext)
	if blocked {
		p.Suspicion.RecordBlock(sessionKey, "critical")
	}
	return blocked, refusal
}

// SanitizeOutput runs post-inference gates. Returns sanitized text and whether
// the response should be withheld (hard block).
func (p *Pipeline) SanitizeOutput(text string, canvasMode bool) (string, bool) {
	if adv := p.Adversarial.AuditOutput(text); adv.Detected {
		log.Printf("[Safety:Output] Adversarial blocked [%s]", adv.Type)
		return adv.Refusal, true
	}

	did := p.Disclosure.ScanOutput(text)
	if did.Detected {
		log.Printf("[Safety:Output] DID [%s / %s]", did.Category, did.Severity)
		if did.Severity == DisclosureCritical {
			return did.Sanitized, true
		}
		text = did.Sanitized
	}

	web := p.WebGuard.ScanOutput(text)
	if web.Detected {
		log.Printf("[Safety:Output] WebGuard [%s / %s]", web.Category, web.Severity)
		text = web.Sanitized
		if web.Severity == DisclosureCritical {
			return text, true
		}
	}

	if canary := p.Canary.ScanOutput(text); canary.Blocked {
		log.Printf("[Safety:Output] Canary trip [%s]", canary.AlertType)
		return canary.Message, true
	}

	if canvasMode {
		canvas := p.Canvas.ScanOutput(text)
		if len(canvas.Violations) > 0 {
			log.Printf("[Safety:Canvas] Sanitised violations: %v", canvas.Violations)
		}
		text = canvas.Sanitized
	}
	return text, false
}

// ConstraintPrompt returns the SCAI contract system fragment for the query,
// plus the constitution and canary honeypot fragment.
func (p *Pipeline) ConstraintPrompt(query string, opts ConstraintOptions) string {
	contract := NewConstraintContract(query, opts)
	parts := []string{
		p.Constitution.GetSystemPrompt(),
		contract.SystemPrompt(),
		p.Canary.SystemPromptFragment(),
	}
	out := ""
	for _, part := range parts {
		if part == "" {
			continue
		}
		if out != "" {
			out += "\n\n"
		}
		out += part
	}
	return out
}
