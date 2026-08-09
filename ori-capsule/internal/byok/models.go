package byok

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"time"
)

// ModelInfo is an OpenAI-shaped model list entry.
type ModelInfo struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	OwnedBy string `json:"owned_by,omitempty"`
	Created int64  `json:"created,omitempty"`
}

// ModelList is an OpenAI-shaped /v1/models response.
type ModelList struct {
	Object string      `json:"object"`
	Data   []ModelInfo `json:"data"`
	Note   string      `json:"note,omitempty"`
}

// ListModels fetches upstream models when possible; falls back to a passthrough stub.
func ListModels(ctx context.Context, cred Credentials) (*ModelList, error) {
	switch cred.Provider {
	case ProviderAnthropic:
		return listAnthropicModels(ctx, cred)
	case ProviderOpenAI, ProviderOpenCode:
		return listOpenAICompatModels(ctx, cred)
	default:
		return stubModels(cred), nil
	}
}

func stubModels(cred Credentials) *ModelList {
	return &ModelList{
		Object: "list",
		Data: []ModelInfo{{
			ID:      "passthrough",
			Object:  "model",
			OwnedBy: string(cred.Provider),
			Created: time.Now().Unix(),
		}},
		Note: "upstream models unavailable — pass the model id on chat/completions",
	}
}

func listOpenAICompatModels(ctx context.Context, cred Credentials) (*ModelList, error) {
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodGet, openAIBase(cred)+"/models", nil)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+cred.APIKey)
	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return stubModels(cred), nil
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if resp.StatusCode >= 300 {
		return stubModels(cred), nil
	}
	var out ModelList
	if err := json.Unmarshal(raw, &out); err != nil {
		return stubModels(cred), nil
	}
	out.Object = "list"
	if len(out.Data) == 0 {
		return stubModels(cred), nil
	}
	return &out, nil
}

func listAnthropicModels(ctx context.Context, cred Credentials) (*ModelList, error) {
	base := strings.TrimRight(cred.BaseURL, "/")
	if base == "" {
		base = "https://api.anthropic.com"
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodGet, base+"/v1/models", nil)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("x-api-key", cred.APIKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")
	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return stubModels(cred), nil
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if resp.StatusCode >= 300 {
		return stubModels(cred), nil
	}
	var ar struct {
		Data []struct {
			ID          string `json:"id"`
			DisplayName string `json:"display_name"`
			CreatedAt   string `json:"created_at"`
		} `json:"data"`
	}
	if err := json.Unmarshal(raw, &ar); err != nil || len(ar.Data) == 0 {
		return stubModels(cred), nil
	}
	out := &ModelList{Object: "list", Data: make([]ModelInfo, 0, len(ar.Data))}
	for _, m := range ar.Data {
		out.Data = append(out.Data, ModelInfo{
			ID:      m.ID,
			Object:  "model",
			OwnedBy: "anthropic",
		})
	}
	return out, nil
}

// IsCanceled reports client disconnect / deadline during upstream calls.
func IsCanceled(err error) bool {
	if err == nil {
		return false
	}
	if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return true
	}
	msg := err.Error()
	return strings.Contains(msg, "context canceled") || strings.Contains(msg, "context deadline")
}
