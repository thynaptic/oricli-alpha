// cmd/gen_dataset/main.go — Dataset generator CLI for Structured Output LoRA training.
//
// Usage:
//   go run ./cmd/gen_dataset --count 200 --out data/sot_train.jsonl
//   go run ./cmd/gen_dataset --count 200 --pb-pull --out data/sot_train.jsonl
//
// Flags:
//   --count  N        examples per schema category (default: 200)
//   --out    path     output JSONL path (default: data/sot_train.jsonl)
//   --pb-pull         pull real sessions from PocketBase (requires PB_URL + PB_TOKEN)
//   --stats           print stats only, do not write file

package main

import (
"context"
"encoding/json"
"flag"
"fmt"
"io"
"log"
"net/http"
"os"
"path/filepath"

"github.com/thynaptic/oricli-go/pkg/training"
)

func main() {
count := flag.Int("count", 200, "examples per schema category")
outPath := flag.String("out", "data/sot_train.jsonl", "output JSONL file path")
pbPull := flag.Bool("pb-pull", false, "pull real sessions from PocketBase")
statsOnly := flag.Bool("stats", false, "print stats only, do not write file")
flag.Parse()

log.Printf("[gen_dataset] count=%d pb_pull=%v out=%s", *count, *pbPull, *outPath)

var pb training.PBLister
if *pbPull {
pb = newEnvPBClient()
if pb == nil {
log.Printf("[gen_dataset] WARNING: --pb-pull set but PB_URL/PB_TOKEN not found — skipping PB pull")
}
}

gen := training.NewDatasetGenerator(pb)
ctx := context.Background()
examples, stats := gen.Generate(ctx, *count)

statsJSON, _ := json.MarshalIndent(stats, "", "  ")
fmt.Printf("\n=== Dataset Stats ===\n%s\n\n", string(statsJSON))

if *statsOnly {
return
}

jsonl, err := gen.ExportJSONL(examples)
if err != nil {
log.Fatalf("[gen_dataset] export error: %v", err)
}

if err := os.MkdirAll(filepath.Dir(*outPath), 0755); err != nil {
log.Fatalf("[gen_dataset] mkdir error: %v", err)
}
if err := os.WriteFile(*outPath, []byte(jsonl), 0644); err != nil {
log.Fatalf("[gen_dataset] write error: %v", err)
}

log.Printf("[gen_dataset] wrote %d examples to %s", len(examples), *outPath)
fmt.Printf("✓ Dataset ready: %s (%d examples)\n", *outPath, len(examples))
fmt.Println("\nNext steps:")
fmt.Println("  1. Upload:   huggingface-cli upload <your-org>/oricli-sot data/sot_train.jsonl")
fmt.Println("  2. Launch RunPod fine-tune pod with config/sot_axolotl.yaml")
fmt.Println("  3. On pod:   axolotl train config.yaml")
fmt.Println("  4. Swap:     bash scripts/swap_ollama_model.sh <gguf_path>")
}

// ─────────────────────────────────────────────────────────────────────────────
// Minimal PocketBase client
// ─────────────────────────────────────────────────────────────────────────────

type envPBClient struct {
baseURL string
token   string
}

func newEnvPBClient() training.PBLister {
baseURL := os.Getenv("PB_URL")
token := os.Getenv("PB_TOKEN")
if baseURL == "" || token == "" {
return nil
}
return &envPBClient{baseURL: baseURL, token: token}
}

func (c *envPBClient) ListRecords(ctx context.Context, collection string, page, perPage int, filter string) ([]map[string]interface{}, error) {
url := fmt.Sprintf("%s/api/collections/%s/records?page=%d&perPage=%d", c.baseURL, collection, page, perPage)
if filter != "" {
url += "&filter=" + filter
}
req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
if err != nil {
return nil, err
}
req.Header.Set("Authorization", "Bearer "+c.token)

resp, err := http.DefaultClient.Do(req)
if err != nil {
return nil, err
}
defer resp.Body.Close()
body, err := io.ReadAll(resp.Body)
if err != nil {
return nil, err
}

var result struct {
Items []map[string]interface{} `json:"items"`
}
if err := json.Unmarshal(body, &result); err != nil {
return nil, fmt.Errorf("unmarshal: %w", err)
}
return result.Items, nil
}
