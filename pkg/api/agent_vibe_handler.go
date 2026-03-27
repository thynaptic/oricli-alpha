package api

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// ─── Schema types mirrored from UI ───────────────────────────────────────────

type vibeRequest struct {
	Message         string        `json:"message"`
	History         []vibeMessage `json:"history"`
	AvailableSkills []string      `json:"available_skills"`
	AvailableRules  []string      `json:"available_rules"`
}

type vibeMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ─── System prompt ────────────────────────────────────────────────────────────

const vibeSystemPrompt = `You are Ori's Agent Architect — a specialist that helps users create sovereign AI agents through natural conversation.

Your job:
1. Understand the user's intent from their description
2. Propose a complete, well-designed agent definition
3. Recommend or generate appropriate skills and rules
4. Respond in a conversational but precise tone — not chatty, not robotic

Always end your response with a JSON block wrapped in triple backticks labeled "agent_proposal".
The JSON must follow this exact schema:
{
  "proposal": {
    "name": "string — concise, title-case agent name",
    "description": "string — one line, what this agent is for",
    "tone": "technical|balanced|casual|formal|creative",
    "color": "string — one of: #C4A44A|#4D9EFF|#06D6A0|#FF6B6B|#A78BFA|#F59E0B",
    "mindset": "string — who this agent IS, 2-4 sentences",
    "instructions": "string — numbered steps this agent follows",
    "constraints": "string — hard limits and refusals",
    "triggers": ["array of trigger phrases"],
    "skills": ["array of skill IDs from available_skills to attach"],
    "rules": ["array of rule IDs from available_rules to enforce"]
  },
  "skills_to_create": [
    {
      "id": "snake_case_id",
      "name": "Title Case Name",
      "description": "one-line desc",
      "mindset": "You are...",
      "instructions": "1. ...\n2. ...",
      "constraints": "Never..."
    }
  ],
  "rules_to_create": [
    {
      "id": "snake_case_id",
      "name": "Title Case Name",
      "description": "one-line desc",
      "constraints": "- require: ...\n- deny: ..."
    }
  ],
  "ready": true,
  "needs_clarification": false,
  "clarification_question": ""
}

Rules:
- If user intent is clear: set ready=true, provide full proposal
- If more info is needed: set ready=false, needs_clarification=true, ask ONE clear question in clarification_question
- Only include skills_to_create if NO existing skill covers the need
- Only include rules_to_create if NO existing rule covers the need
- Keep mindset/instructions focused and sovereign — no hedging or assistant-speak
- The proposal object must ALWAYS be present even if needs_clarification is true (provide best guess)`

// ─── Handler ──────────────────────────────────────────────────────────────────

// handleAgentVibe streams an agent proposal from ORI based on user description.
// POST /v1/agents/vibe
func (s *ServerV2) handleAgentVibe(c *gin.Context) {
	var req vibeRequest
	if err := c.ShouldBindJSON(&req); err != nil || req.Message == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "message is required"})
		return
	}

	// Build context about available skills/rules
	contextParts := []string{}
	if len(req.AvailableSkills) > 0 {
		contextParts = append(contextParts, "Available skill IDs: "+strings.Join(req.AvailableSkills, ", "))
	}
	if len(req.AvailableRules) > 0 {
		contextParts = append(contextParts, "Available rule IDs: "+strings.Join(req.AvailableRules, ", "))
	}

	// Build message list
	msgs := []map[string]string{
		{"role": "system", "content": vibeSystemPrompt},
	}
	if len(contextParts) > 0 {
		msgs = append(msgs, map[string]string{
			"role":    "system",
			"content": "Context:\n" + strings.Join(contextParts, "\n"),
		})
	}
	for _, m := range req.History {
		msgs = append(msgs, map[string]string{"role": m.Role, "content": m.Content})
	}
	msgs = append(msgs, map[string]string{"role": "user", "content": req.Message})

	genSvc := s.Agent.GenService
	if genSvc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "generation service unavailable"})
		return
	}

	tokenCh, err := genSvc.ChatStream(c.Request.Context(), msgs, map[string]interface{}{})
	if err != nil {
		log.Printf("[AgentVibe] ChatStream error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("X-Accel-Buffering", "no")

	flusher, canFlush := c.Writer.(http.Flusher)
	for token := range tokenCh {
		chunk := map[string]any{
			"choices": []map[string]any{
				{"delta": map[string]any{"content": token}},
			},
		}
		b, _ := json.Marshal(chunk)
		fmt.Fprintf(c.Writer, "data: %s\n\n", b)
		if canFlush {
			flusher.Flush()
		}
	}
	fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
	if canFlush {
		flusher.Flush()
	}
}

