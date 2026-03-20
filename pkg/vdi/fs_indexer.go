package vdi

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/memory"
)

// --- Pillar 55: Sovereign Filesystem Indexer ---
// Recursively maps the local substrate into the Working Memory Graph (COGS).

type FSIndexer struct {
	Graph *memory.WorkingMemoryGraph
}

func NewFSIndexer(graph *memory.WorkingMemoryGraph) *FSIndexer {
	return &FSIndexer{Graph: graph}
}

// IndexRecursive walks the provided root and adds matched files to the graph.
func (s *FSIndexer) IndexRecursive(root string) error {
	log.Printf("[FSIndexer] Mapping substrate at: %s", root)

	extensions := map[string]bool{
		".go":   true,
		".md":   true,
		".py":   true,
		".ori":  true,
		".json": true,
		".sh":   true,
	}

	count := 0
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil { return err }
		if info.IsDir() {
			// Skip hidden dirs
			if strings.HasPrefix(info.Name(), ".") && info.Name() != "." {
				return filepath.SkipDir
			}
			return nil
		}

		ext := filepath.Ext(path)
		if extensions[ext] {
			// Add to graph
			s.Graph.AddEntity(info.Name(), memory.TypeThing, fmt.Sprintf("File path: %s | Size: %d bytes", path, info.Size()), 0.5, 0.5, 0.5)
			count++
		}
		return nil
	})

	if err == nil {
		log.Printf("[FSIndexer] Successfully mapped %d substrate nodes to COGS graph.", count)
	}
	return err
}
