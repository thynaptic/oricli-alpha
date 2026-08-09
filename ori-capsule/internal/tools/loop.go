package tools

import (
	"context"
	"fmt"
	"strings"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

const DefaultMaxRounds = 4

// LoopOptions configures the server-side tool execution loop.
type LoopOptions struct {
	MaxRounds int
	// InjectSchemas adds registry tools when the request has none.
	InjectSchemas bool
}

// RunAutoLoop calls the model, executes allowlisted tool_calls, and re-calls
// until finish_reason != tool_calls or MaxRounds is hit.
func RunAutoLoop(ctx context.Context, cred byok.Credentials, req byok.ChatRequest, reg *Registry, opts LoopOptions) (*byok.ChatResponse, error) {
	if opts.MaxRounds <= 0 {
		opts.MaxRounds = DefaultMaxRounds
	}
	if opts.InjectSchemas && len(req.Tools) == 0 && reg != nil {
		req.Tools = reg.Schemas()
	}
	if len(req.Tools) == 0 {
		return byok.ChatNonStream(ctx, cred, req)
	}
	req.Stream = false
	if req.ToolChoice == nil {
		req.ToolChoice = "auto"
	}

	var last *byok.ChatResponse
	for round := 0; round < opts.MaxRounds; round++ {
		out, err := byok.ChatNonStream(ctx, cred, req)
		if err != nil {
			return nil, err
		}
		last = out
		if len(out.Choices) == 0 {
			return out, nil
		}
		ch := out.Choices[0]
		if ch.FinishReason != "tool_calls" || len(ch.Message.ToolCalls) == 0 {
			return out, nil
		}
		if reg == nil {
			return out, nil
		}
		// Append assistant tool call turn + tool results, then continue.
		req.Messages = append(req.Messages, ch.Message)
		req.Messages = append(req.Messages, reg.ExecuteCalls(ch.Message.ToolCalls)...)
	}
	if last == nil {
		return nil, fmt.Errorf("tool loop produced no response")
	}
	// Cap hit while still requesting tools — return last tool_calls turn.
	if len(last.Choices) > 0 && last.Choices[0].FinishReason == "tool_calls" {
		last.Choices[0].Message.Content = strings.TrimSpace(last.Choices[0].Message.Content +
			"\n\n[ori-capsule] tool loop reached max rounds; returning last tool_calls to client")
	}
	return last, nil
}
