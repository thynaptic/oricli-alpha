package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"github.com/thynaptic/oricli-go/pkg/cli"
)

var (
	flagTarget string
	flagKey    string
	flagModel  string
	flagStream bool
)

func main() {
	root := &cobra.Command{
		Use:   "oricli",
		Short: "Oricli — Sovereign Intelligence CLI",
		Long: `Oricli CLI — interact with the Oricli backbone.

  Interactive REPL:  oricli
  One-shot chat:     oricli ask "explain goroutines"
  Subcommands:       oricli health | oricli models | oricli modules`,
		Args:           cobra.NoArgs,
		SilenceUsage:   true,
		RunE:           runRoot,
	}

	root.PersistentFlags().StringVar(&flagTarget, "target", "", "API target (overrides config/env)")
	root.PersistentFlags().StringVar(&flagKey, "key", "", "API key (overrides config/env)")
	root.PersistentFlags().StringVar(&flagModel, "model", "", "Model to use (overrides config/env)")
	root.PersistentFlags().BoolVar(&flagStream, "no-stream", false, "Disable streaming (blocking mode)")

	root.AddCommand(cmdAsk(), cmdHealth(), cmdModels(), cmdModules(), cmdMetrics(), cmdTherapy(), cmdGoals(), cmdConfig())

	if err := root.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func loadClient() (*cli.Config, *cli.Client, error) {
	cfg, err := cli.LoadConfig()
	if err != nil {
		return nil, nil, err
	}
	// Apply flag overrides
	if flagTarget != "" {
		cfg.Target = flagTarget
	}
	if flagKey != "" {
		cfg.APIKey = flagKey
	}
	if flagModel != "" {
		cfg.Model = flagModel
	}
	return cfg, cli.NewClient(cfg), nil
}

// ── Root command — interactive REPL ──────────────────────────────────────────

func runRoot(cmd *cobra.Command, args []string) error {
	cfg, client, err := loadClient()
	if err != nil {
		return err
	}
	// Interactive REPL
	return cli.Run(cfg, client)
}

// ── ask subcommand — one-shot chat ────────────────────────────────────────────

func cmdAsk() *cobra.Command {
	return &cobra.Command{
		Use:   "ask <message...>",
		Short: "One-shot chat query",
		Example: `  oricli ask "explain goroutines in one sentence"
  oricli ask what is the capital of France`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, client, err := loadClient()
			if err != nil {
				return err
			}
			return cli.OneShot(cfg, client, strings.Join(args, " "))
		},
	}
}

// ── Standalone subcommands (non-interactive shortcuts) ────────────────────────

func cmdHealth() *cobra.Command {
	return &cobra.Command{
		Use:   "health",
		Short: "Backbone health check",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.GetHealth()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	}
}

func cmdModels() *cobra.Command {
	return &cobra.Command{
		Use:   "models",
		Short: "List available models",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.GetModels()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	}
}

func cmdModules() *cobra.Command {
	return &cobra.Command{
		Use:   "modules",
		Short: "List all brain modules",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.GetModules()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	}
}

func cmdMetrics() *cobra.Command {
	return &cobra.Command{
		Use:   "metrics",
		Short: "Runtime metrics",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.GetMetrics()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	}
}

func cmdTherapy() *cobra.Command {
	return &cobra.Command{
		Use:   "therapy",
		Short: "Therapy stats + session formulation",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			stats, err := client.GetTherapyStats()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(stats)
			form, err := client.GetFormulation()
			if err == nil {
				fmt.Println("---")
				printJSON(form)
			}
			return nil
		},
	}
}

func cmdGoals() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "goals",
		Short: "List or create sovereign goals",
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.GetGoals()
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	}

	cmd.AddCommand(&cobra.Command{
		Use:   "new <description>",
		Short: "Create a new sovereign goal",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			_, client, err := loadClient()
			if err != nil {
				return err
			}
			data, err := client.PostGoal(strings.Join(args, " "))
			if err != nil {
				fmt.Fprintln(os.Stderr, "✗ "+err.Error())
				os.Exit(1)
			}
			printJSON(data)
			return nil
		},
	})

	return cmd
}

func cmdConfig() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Manage CLI config (~/.oricli/config.yaml)",
	}

	cmd.AddCommand(&cobra.Command{
		Use:   "show",
		Short: "Show current config",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, _, err := loadClient()
			if err != nil {
				return err
			}
			fmt.Printf("target:  %s\n", cfg.Target)
			fmt.Printf("model:   %s\n", cfg.Model)
			fmt.Printf("api_key: %s\n", maskKey(cfg.APIKey))
			fmt.Printf("stream:  %v\n", cfg.Stream)
			return nil
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "set-target <url>",
		Short: "Set and save the API target",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, _, err := loadClient()
			if err != nil {
				return err
			}
			cfg.Target = args[0]
			if err := cfg.Save(); err != nil {
				return err
			}
			fmt.Printf("✓ Target saved: %s\n", cfg.Target)
			return nil
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "set-key <key>",
		Short: "Set and save the API key",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, _, err := loadClient()
			if err != nil {
				return err
			}
			cfg.APIKey = args[0]
			if err := cfg.Save(); err != nil {
				return err
			}
			fmt.Printf("✓ API key saved\n")
			return nil
		},
	})

	return cmd
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func printJSON(v interface{}) {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}

func maskKey(k string) string {
	if len(k) <= 8 {
		return "***"
	}
	return k[:6] + "…" + k[len(k)-4:]
}
