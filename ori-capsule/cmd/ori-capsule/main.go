// Command ori-capsule is the dockerized BYOK ORI runtime (working name).
//
// No VPS daemons. Inference is Bring-Your-Own-Key:
// OpenAI, Anthropic, or any OpenCode / OpenAI-compatible base URL.
package main

import (
	"log"

	"github.com/joho/godotenv"
	"github.com/thynaptic/ori-capsule/internal/api"
	"github.com/thynaptic/ori-capsule/internal/config"
)

func main() {
	_ = godotenv.Load()
	cfg := config.Load()
	log.Printf("ori-capsule starting on :%d (BYOK + safety + memory + gosh)", cfg.Port)
	if cfg.CapsuleKey != "" {
		log.Printf("gateway lock enabled (ORI_CAPSULE_KEY) — pass LLM key via X-API-Key")
	}
	log.Printf("memory dir=%s max_turns=%d", cfg.MemoryDir, cfg.MaxSessionTurns)
	if cfg.GoshEnabled {
		mode := "mem"
		if !cfg.GoshForceMem && cfg.GoshWorkspace != "" {
			mode = "overlay:" + cfg.GoshWorkspace
		}
		log.Printf("gosh enabled mode=%s timeout=%s", mode, cfg.GoshExecTimeout)
	} else {
		log.Printf("gosh disabled")
	}
	srv := api.New(cfg)
	if err := srv.Run(); err != nil {
		log.Fatal(err)
	}
}
