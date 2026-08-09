package config

import "testing"

func TestSplitCSVKeepsURLOrigins(t *testing.T) {
	got := splitCSV("http://localhost:3000, https://app.example.com")
	if len(got) != 2 || got[0] != "http://localhost:3000" || got[1] != "https://app.example.com" {
		t.Fatalf("splitCSV = %#v", got)
	}
	if got := splitCSV("*"); len(got) != 1 || got[0] != "*" {
		t.Fatalf("wildcard = %#v", got)
	}
}
