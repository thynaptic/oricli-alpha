package service

import (
	"context"
	"fmt"
	"time"

	"github.com/thynaptic/oricli-go/pkg/gosh"
)

// GoshModule implements the ModuleInstance interface for the Go-native shell sandbox.
type GoshModule struct {
	session *gosh.Session
	name    string
}

// NewGoshModule creates a new Gosh-backed Hive module.
func NewGoshModule(name string, baseDir string) (*GoshModule, error) {
	session, err := gosh.NewOverlaySession(baseDir)
	if err != nil {
		return nil, err
	}
	return &GoshModule{
		session: session,
		name:    name,
	}, nil
}

func (m *GoshModule) Initialize(ctx context.Context) error {
	return nil
}

func (m *GoshModule) Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error) {
	switch operation {
	case "execute":
		script, ok := params["script"].(string)
		if !ok {
			return nil, fmt.Errorf("missing 'script' parameter")
		}
		start := time.Now()
		output, err := m.session.Execute(ctx, script)
		duration := time.Since(start).Seconds()
		
		success := err == nil
		exitCode := 0
		if !success {
			exitCode = 1
		}

		return ExecutionResult{
			Success:       success,
			Stdout:        output,
			ExitCode:      exitCode,
			ExecutionTime: duration,
		}, nil

	case "write":
		path, ok := params["path"].(string)
		if !ok {
			return nil, fmt.Errorf("missing 'path' parameter")
		}
		content, ok := params["content"].(string)
		if !ok {
			return nil, fmt.Errorf("missing 'content' parameter")
		}
		err := m.session.WriteFile(path, []byte(content))
		return err == nil, err

	case "read":
		path, ok := params["path"].(string)
		if !ok {
			return nil, fmt.Errorf("missing 'path' parameter")
		}
		data, err := m.session.ReadFile(path)
		if err != nil {
			return nil, err
		}
		return string(data), nil

	default:
		return nil, fmt.Errorf("unknown operation: %s", operation)
	}
}

func (m *GoshModule) Metadata() ModuleMetadata {
	return ModuleMetadata{
		Name:        m.name,
		Version:     "1.0.0",
		Description: "Sovereign Go-native Bash Sandbox with Overlay FS",
		Author:      "Oricli-Alpha Core",
		IsGoNative:  true,
		Operations:  []string{"execute", "write", "read"},
	}
}

func (m *GoshModule) Cleanup(ctx context.Context) error {
	return nil
}
