package gosh

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/afero"
	"github.com/traefik/yaegi/interp"
	"github.com/traefik/yaegi/stdlib"
	"mvdan.cc/sh/v3/expand"
	shinterp "mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

// DynamicHandler is a function type for tools created at runtime by agents.
type DynamicHandler func(args []string) (string, string, error)

// Session represents an isolated, virtualized shell environment.
type Session struct {
	fs           afero.Fs
	env          []string
	dir          string
	stdout       bytes.Buffer
	stderr       bytes.Buffer
	dynamicTools map[string]DynamicHandler
}

// NewSession creates a new virtual shell session with a clean in-memory filesystem.
func NewSession() *Session {
	fs := afero.NewMemMapFs()
	fs.MkdirAll("/", 0777)
	return &Session{
		fs:           fs,
		env:          []string{"PATH=/bin:/usr/bin", "HOME=/", "PWD=/"},
		dir:          "/",
		dynamicTools: make(map[string]DynamicHandler),
	}
}

// NewOverlaySession creates a session that can read the host FS but only writes to memory.
func NewOverlaySession(baseDir string) (*Session, error) {
	absBase, err := filepath.Abs(baseDir)
	if err != nil {
		return nil, err
	}
	
	// Jail the base to the project root. 
	// This ensures that any path (including absolute ones) stays inside the baseDir.
	base := afero.NewReadOnlyFs(afero.NewBasePathFs(afero.NewOsFs(), absBase))
	mem := afero.NewMemMapFs()
	fs := afero.NewCopyOnWriteFs(base, mem)
	
	return &Session{
		fs:  fs,
		env: []string{
			"PATH=/bin:/usr/bin",
			"HOME=/",
			"PWD=/",
		},
		dir:          "/",
		dynamicTools: make(map[string]DynamicHandler),
	}, nil
}

// RegisterTool allows an agent to hot-load a Go-native tool into the shell registry.
func (s *Session) RegisterTool(name string, sourceCode string) error {
	i := interp.New(interp.Options{})
	i.Use(stdlib.Symbols)

	_, err := i.Eval(sourceCode)
	if err != nil {
		return fmt.Errorf("failed to interpret tool source: %w", err)
	}

	v, err := i.Eval(fmt.Sprintf("main.%s", strings.Title(name)))
	if err != nil {
		// Try lowercase if Title case fails
		v, err = i.Eval(fmt.Sprintf("main.%s", name))
		if err != nil {
			return fmt.Errorf("could not find handler function '%s' in source: %w", name, err)
		}
	}

	handler, ok := v.Interface().(func([]string) (string, string, error))
	if !ok {
		return fmt.Errorf("tool handler has wrong signature; expected func([]string) (string, string, error)")
	}

	s.dynamicTools[name] = handler
	return nil
}

// resolvePath ensures that paths are resolved against the interpreter's current working directory.
func (s *Session) resolvePath(ctx context.Context, path string) string {
	if filepath.IsAbs(path) {
		// If it's absolute, it's already "rooted" in our jail.
		return path
	}
	return filepath.Join(shinterp.HandlerCtx(ctx).Dir, path)
}

// Execute runs a bash script within the virtual environment.
func (s *Session) Execute(ctx context.Context, script string) (string, error) {
	parser := syntax.NewParser()
	f, err := parser.Parse(strings.NewReader(script), "")
	if err != nil {
		return "", fmt.Errorf("failed to parse script: %w", err)
	}

	s.stdout.Reset()
	s.stderr.Reset()

	// Map Afero to interp handlers
	r, err := shinterp.New(
		shinterp.StdIO(nil, &s.stdout, &s.stderr),
		shinterp.Env(expand.ListEnviron(s.env...)),
		shinterp.Dir(s.dir),
		
		shinterp.OpenHandler(func(ctx context.Context, path string, flag int, perm os.FileMode) (io.ReadWriteCloser, error) {
			return s.fs.OpenFile(s.resolvePath(ctx, path), flag, perm)
		}),
		shinterp.StatHandler(func(ctx context.Context, path string, followSymlinks bool) (os.FileInfo, error) {
			return s.fs.Stat(s.resolvePath(ctx, path))
		}),
		shinterp.ReadDirHandler(func(ctx context.Context, path string) ([]os.FileInfo, error) {
			return afero.ReadDir(s.fs, s.resolvePath(ctx, path))
		}),
		
		shinterp.ExecHandler(s.execHandler),
	)
	if err != nil {
		return "", fmt.Errorf("failed to initialize interpreter: %w", err)
	}

	err = r.Run(ctx, f)
	s.dir = r.Dir
	
	output := s.stdout.String()
	if err != nil {
		return output, fmt.Errorf("execution error: %w (stderr: %s)", err, s.stderr.String())
	}

	return output, nil
}

// ExecHandler bridges the shell to Go-native tool implementations.
func (s *Session) execHandler(ctx context.Context, args []string) error {
	hc := shinterp.HandlerCtx(ctx)
	binary := args[0]

	// Check for dynamic tools first
	if handler, ok := s.dynamicTools[binary]; ok {
		stdout, stderr, err := handler(args[1:])
		fmt.Fprint(hc.Stdout, stdout)
		fmt.Fprint(hc.Stderr, stderr)
		return err
	}

	switch binary {
	case "cat":
		if len(args) < 2 {
			return nil
		}
		for _, arg := range args[1:] {
			path := s.resolvePath(ctx, arg)
			data, err := afero.ReadFile(s.fs, path)
			if err != nil {
				fmt.Fprintf(hc.Stderr, "cat: %s: %v\n", arg, err)
				return err
			}
			hc.Stdout.Write(data)
		}
		return nil

	case "ls":
		path := "."
		if len(args) > 1 {
			path = args[1]
		}
		resolved := s.resolvePath(ctx, path)
		info, err := s.fs.Stat(resolved)
		if err != nil {
			fmt.Fprintf(hc.Stderr, "ls: %s: %v\n", path, err)
			return err
		}

		if !info.IsDir() {
			fmt.Fprintln(hc.Stdout, info.Name())
			return nil
		}

		infos, err := afero.ReadDir(s.fs, resolved)
		if err != nil {
			fmt.Fprintf(hc.Stderr, "ls: %s: %v\n", path, err)
			return err
		}
		for _, info := range infos {
			fmt.Fprintln(hc.Stdout, info.Name())
		}
		return nil

	case "mkdir":
		if len(args) < 2 {
			return nil
		}
		for _, arg := range args[1:] {
			err := s.fs.MkdirAll(s.resolvePath(ctx, arg), 0777)
			if err != nil {
				fmt.Fprintf(hc.Stderr, "mkdir: %s: %v\n", arg, err)
				return err
			}
		}
		return nil

	case "rm":
		if len(args) < 2 {
			return nil
		}
		for _, arg := range args[1:] {
			err := s.fs.RemoveAll(s.resolvePath(ctx, arg))
			if err != nil {
				fmt.Fprintf(hc.Stderr, "rm: %s: %v\n", arg, err)
				return err
			}
		}
		return nil

	case "pwd":
		fmt.Fprintln(hc.Stdout, hc.Dir)
		return nil

	case "echo":
		fmt.Fprintln(hc.Stdout, strings.Join(args[1:], " "))
		return nil

	default:
		return fmt.Errorf("restricted: %s is not permitted in this agent sandbox", binary)
	}
}

// WriteFile is a helper for the Go backbone to seed the sandbox.
func (s *Session) WriteFile(path string, data []byte) error {
	return afero.WriteFile(s.fs, path, data, 0666)
}

// ReadFile is a helper for the Go backbone to extract results.
func (s *Session) ReadFile(path string) ([]byte, error) {
	return afero.ReadFile(s.fs, path)
}
