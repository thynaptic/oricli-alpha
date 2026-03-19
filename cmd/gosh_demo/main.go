package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/gosh"
)

func main() {
	fmt.Println("--- Gosh Sandbox Test Run (Oricli-Alpha v2.0) ---")

	// 1. Initialize an Overlay Session on the Mavaia project root
	// We'll use the current directory (should be Mavaia root)
	s, err := gosh.NewOverlaySession(".")
	if err != nil {
		log.Fatalf("Failed to create Overlay Session: %v", err)
	}

	ctx := context.Background()

	// 2. Scenario: Discovery
	fmt.Println("\n[Scenario 1: Discovery]")
	fmt.Println("Agent runs: 'ls pkg/gosh'")
	output, err := s.Execute(ctx, "ls pkg/gosh")
	if err != nil {
		fmt.Printf("Error: %v (output: %s)\n", err, output)
	} else {
		fmt.Printf("Agent sees contents of pkg/gosh:\n%s", output)
	}

	// 3. Scenario: Refactoring
	fmt.Println("\n[Scenario 2: Memory-Layer 'Hacking']")
	refactorScript := `
echo "// Gosh Verified Refactor v2.0" > pkg/gosh/session.go
echo "package gosh" >> pkg/gosh/session.go
echo "// ... simulated logic for the new world order ..." >> pkg/gosh/session.go
`
	fmt.Println("Agent is 'writing' a refactored session.go into the memory layer...")
	_, err = s.Execute(ctx, refactorScript)
	if err != nil {
		fmt.Printf("Error during 'hack': %v\n", err)
	}

	// 4. Verification (Inside)
	fmt.Println("\n[Scenario 3: Inside-Sandbox Verification]")
	fmt.Println("Agent runs: 'cat pkg/gosh/session.go'")
	output, _ = s.Execute(ctx, "cat pkg/gosh/session.go")
	fmt.Printf("Virtualized Content in Gosh:\n%s", output)

	// 5. Verification (Outside)
	fmt.Println("\n[Scenario 4: Host Protection Check]")
	hostData, err := os.ReadFile("pkg/gosh/session.go")
	if err != nil {
		log.Fatalf("Failed to read host file: %v", err)
	}
	
	firstLine := strings.Split(string(hostData), "\n")[0]
	fmt.Printf("REAL file on VPS (First Line): %s\n", firstLine)

	if firstLine == "// Gosh Verified Refactor v2.0" {
		fmt.Println("\n!!! CRITICAL SECURITY BREACH: Host was modified !!!")
	} else {
		fmt.Println("\n--- Test Run Success: Sandbox Integrity Verified ---")
		fmt.Println("The host file remains untouched while the agent 'hallucinates' success.")
	}
}
