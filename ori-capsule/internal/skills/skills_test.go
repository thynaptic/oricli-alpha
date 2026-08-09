package skills_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/skills"
)

func TestLibrary_Match(t *testing.T) {
	dir := t.TempDir()
	content := `@skill_name: demo_skill
@description: Demo
@triggers: ["goroutine", "golang-demo"]

<mindset>
Think in goroutines.
</mindset>
`
	if err := os.WriteFile(filepath.Join(dir, "demo.ori"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	lib := skills.Open(dir)
	if n := len(lib.List()); n != 1 {
		t.Fatalf("list=%d", n)
	}
	got := lib.Match("please help with a goroutine leak")
	if !strings.Contains(got, "demo_skill") || !strings.Contains(got, "Think in goroutines") {
		t.Fatalf("match=%q", got)
	}
	if lib.Match("unrelated topic") != "" {
		t.Fatal("expected no match")
	}
}

func TestLibrary_MissingDir(t *testing.T) {
	lib := skills.Open("/nonexistent/skills")
	if len(lib.List()) != 0 {
		t.Fatal("expected empty")
	}
}
