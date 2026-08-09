package byok_test

import (
	"testing"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

func TestParseProvider(t *testing.T) {
	cases := map[string]byok.Provider{
		"openai":    byok.ProviderOpenAI,
		"OpenAI":    byok.ProviderOpenAI,
		"anthropic": byok.ProviderAnthropic,
		"opencode":  byok.ProviderOpenCode,
		"":          byok.ProviderOpenAI,
	}
	for in, want := range cases {
		got, err := byok.ParseProvider(in)
		if err != nil {
			t.Fatalf("ParseProvider(%q): %v", in, err)
		}
		if got != want {
			t.Fatalf("ParseProvider(%q)=%q want %q", in, got, want)
		}
	}
	if _, err := byok.ParseProvider("nope"); err == nil {
		t.Fatal("expected error for unknown provider")
	}
}
