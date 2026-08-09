package forge_test

import (
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/forge"
)

func TestScriptConstitution_AllowsEcho(t *testing.T) {
	c := forge.NewScriptConstitution()
	v, ok := c.Check("echo hi\ncat /in.txt")
	if !ok {
		t.Fatalf("expected pass, got %v", v)
	}
}

func TestScriptConstitution_BlocksCurl(t *testing.T) {
	c := forge.NewScriptConstitution()
	v, ok := c.Check("curl https://example.com")
	if ok {
		t.Fatal("expected fail")
	}
	found := false
	for _, x := range v {
		if x.Rule == "no_restricted_binaries" || x.Rule == "no_network_to_unknown" {
			found = true
		}
	}
	if !found {
		t.Fatalf("violations=%v", v)
	}
}

func TestScriptConstitution_BlocksRmRf(t *testing.T) {
	c := forge.NewScriptConstitution()
	_, ok := c.Check("rm -rf /")
	if ok {
		t.Fatal("expected fatal")
	}
}

func TestToolConstitution_RequiresContract(t *testing.T) {
	c := forge.NewToolConstitution()
	_, ok := c.Check("echo hi")
	if ok {
		t.Fatal("echo-only should fail tool contract (stdin+json warnings)")
	}
}

func TestCheckGoSource_BlocksTODO(t *testing.T) {
	_, ok := forge.CheckGoSource("package main\nfunc main() {\n// TODO: later\n}\n")
	if ok {
		t.Fatal("expected fail on TODO")
	}
}

func TestCheckGoSource_BlocksExec(t *testing.T) {
	src := `package main
import "os/exec"
func main() { exec.Command("ls") }
`
	v, ok := forge.CheckGoSource(src)
	if ok {
		t.Fatal("expected fail")
	}
	if len(v) == 0 || !strings.Contains(v[0].Rule, "escape") {
		t.Fatalf("violations=%v", v)
	}
}

func TestVerifyStatic_PassAndFail(t *testing.T) {
	ok := forge.VerifyStatic(forge.VerifyRequest{Script: "echo ok"})
	if !ok.OK {
		t.Fatalf("%+v", ok)
	}
	bad := forge.VerifyStatic(forge.VerifyRequest{Script: "sudo rm -rf /"})
	if bad.OK || bad.Stage == "" {
		t.Fatalf("%+v", bad)
	}
}
