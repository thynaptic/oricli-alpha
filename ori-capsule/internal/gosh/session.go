// Package gosh is the docker-friendly sovereign shell sandbox for ori-capsule.
//
// Pure Go (no CGO, no subprocesses). Default mode is in-memory. Optional
// overlay mounts ORI_GOSH_WORKSPACE as a read-only jail with copy-on-write
// memory for writes — host/volume files are never modified.
//
// Not included: Hive/daemon sharing, VPS host paths, real go build/vet exec.
package gosh

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
	"unicode"

	"github.com/spf13/afero"
	"github.com/thynaptic/ori-capsule/internal/forge"
	"github.com/traefik/yaegi/interp"
	"github.com/traefik/yaegi/stdlib"
	"mvdan.cc/sh/v3/expand"
	shinterp "mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

// DynamicHandler is a Yaegi-loaded tool: args → stdout, stderr, err.
type DynamicHandler func(args []string) (string, string, error)

// Session is an isolated virtual shell environment.
type Session struct {
	fs           afero.Fs
	env          []string
	dir          string
	stdout       bytes.Buffer
	stderr       bytes.Buffer
	dynamicTools map[string]DynamicHandler
	workspace    string // empty when mem-only
	mode         string // "mem" | "overlay"
}

// NewMemSession creates a fully isolated in-memory sandbox (no host FS).
func NewMemSession() *Session {
	fs := afero.NewMemMapFs()
	_ = fs.MkdirAll("/", 0o777)
	return &Session{
		fs:           fs,
		env:          []string{"PATH=/bin:/usr/bin", "HOME=/", "PWD=/", "ORI_GOSH_MODE=mem"},
		dir:          "/",
		dynamicTools: make(map[string]DynamicHandler),
		mode:         "mem",
	}
}

// NewOverlaySession jails reads to workspaceDir (read-only) and keeps writes
// in memory. workspaceDir should be a container mount (e.g. /workspace).
func NewOverlaySession(workspaceDir string) (*Session, error) {
	absBase, err := filepath.Abs(workspaceDir)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(absBase)
	if err != nil {
		return nil, fmt.Errorf("gosh workspace %q: %w", absBase, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("gosh workspace %q is not a directory", absBase)
	}
	base := afero.NewReadOnlyFs(afero.NewBasePathFs(afero.NewOsFs(), absBase))
	mem := afero.NewMemMapFs()
	fs := afero.NewCopyOnWriteFs(base, mem)
	return &Session{
		fs: fs,
		env: []string{
			"PATH=/bin:/usr/bin",
			"HOME=/",
			"PWD=/",
			"ORI_GOSH_MODE=overlay",
			"ORI_GOSH_WORKSPACE=" + absBase,
		},
		dir:          "/",
		dynamicTools: make(map[string]DynamicHandler),
		workspace:    absBase,
		mode:         "overlay",
	}, nil
}

// Mode returns "mem" or "overlay".
func (s *Session) Mode() string { return s.mode }

// Workspace returns the overlay base path (empty for mem).
func (s *Session) Workspace() string { return s.workspace }

// RegisterTool hot-loads a Go tool via Yaegi.
// Handler must be: func Name(args []string) (stdout, stderr string, err error)
func (s *Session) RegisterTool(name, sourceCode string) error {
	name = strings.TrimSpace(name)
	if name == "" {
		return fmt.Errorf("tool name required")
	}
	i := interp.New(interp.Options{})
	i.Use(stdlib.Symbols)
	if _, err := i.Eval(sourceCode); err != nil {
		return fmt.Errorf("interpret tool source: %w", err)
	}
	exported := exportName(name)
	v, err := i.Eval("main." + exported)
	if err != nil {
		v, err = i.Eval("main." + name)
		if err != nil {
			return fmt.Errorf("handler %q not found in source: %w", name, err)
		}
	}
	handler, ok := v.Interface().(func([]string) (string, string, error))
	if !ok {
		return fmt.Errorf("tool handler wrong signature; want func([]string) (string, string, error)")
	}
	s.dynamicTools[name] = handler
	return nil
}

func exportName(name string) string {
	r := []rune(name)
	if len(r) == 0 {
		return name
	}
	r[0] = unicode.ToUpper(r[0])
	return string(r)
}

func (s *Session) resolvePath(ctx context.Context, path string) string {
	if filepath.IsAbs(path) {
		return path
	}
	return filepath.Join(shinterp.HandlerCtx(ctx).Dir, path)
}

// Execute runs a POSIX script in-process (allowlisted builtins + dynamic tools).
func (s *Session) Execute(ctx context.Context, script string) (string, error) {
	parser := syntax.NewParser()
	f, err := parser.Parse(strings.NewReader(script), "")
	if err != nil {
		return "", fmt.Errorf("parse script: %w", err)
	}
	s.stdout.Reset()
	s.stderr.Reset()

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
		return "", fmt.Errorf("init interpreter: %w", err)
	}
	err = r.Run(ctx, f)
	s.dir = r.Dir
	out := s.stdout.String()
	if err != nil {
		return out, fmt.Errorf("execution error: %w (stderr: %s)", err, s.stderr.String())
	}
	return out, nil
}

func (s *Session) execHandler(ctx context.Context, args []string) error {
	hc := shinterp.HandlerCtx(ctx)
	if len(args) == 0 {
		return nil
	}
	binary := args[0]

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
			_, _ = hc.Stdout.Write(data)
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
		for _, fi := range infos {
			fmt.Fprintln(hc.Stdout, fi.Name())
		}
		return nil
	case "mkdir":
		for _, arg := range args[1:] {
			if err := s.fs.MkdirAll(s.resolvePath(ctx, arg), 0o777); err != nil {
				fmt.Fprintf(hc.Stderr, "mkdir: %s: %v\n", arg, err)
				return err
			}
		}
		return nil
	case "rm":
		for _, arg := range args[1:] {
			if err := s.fs.RemoveAll(s.resolvePath(ctx, arg)); err != nil {
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

func (s *Session) WriteFile(path string, data []byte) error {
	return afero.WriteFile(s.fs, path, data, 0o666)
}

func (s *Session) ReadFile(path string) ([]byte, error) {
	return afero.ReadFile(s.fs, path)
}

// RunGoSource interprets package main via Yaegi (no subprocess).
func (s *Session) RunGoSource(ctx context.Context, source string) (stdout, stderr string, err error) {
	_ = ctx
	var outBuf, errBuf bytes.Buffer
	i := interp.New(interp.Options{Stdout: &outBuf, Stderr: &errBuf})
	i.Use(stdlib.Symbols)
	defer func() {
		if r := recover(); r != nil {
			stderr = fmt.Sprintf("panic: %v", r)
			err = fmt.Errorf("panic in interpreted code: %v", r)
		}
	}()
	if _, evalErr := i.Eval(source); evalErr != nil {
		return outBuf.String(), errBuf.String() + evalErr.Error(), evalErr
	}
	mainFn, evalErr := i.Eval("main.main")
	if evalErr != nil {
		return outBuf.String(), errBuf.String() + evalErr.Error(), evalErr
	}
	fn, ok := mainFn.Interface().(func())
	if !ok {
		return outBuf.String(), errBuf.String(), fmt.Errorf("main.main has unexpected type")
	}
	fn()
	return outBuf.String(), errBuf.String(), nil
}

// --- Manager (docker-facing) ---

// Config for the capsule GOSH surface.
type Config struct {
	Enabled     bool
	Workspace   string // empty → mem-only; else overlay if dir exists
	ForceMem    bool   // ignore workspace even if set
	ExecTimeout time.Duration
}

// Manager opens per-request sessions (no shared daemon state across sandboxes).
// ActionTracker is process-local and keyed by conversation/session id.
type Manager struct {
	cfg     Config
	actions *ActionTracker
}

func NewManager(cfg Config) *Manager {
	if cfg.ExecTimeout <= 0 {
		cfg.ExecTimeout = 5 * time.Second
	}
	return &Manager{cfg: cfg, actions: NewActionTracker(24)}
}

// Actions returns the shared action / mismatch tracker.
func (m *Manager) Actions() *ActionTracker {
	if m == nil {
		return nil
	}
	return m.actions
}

func (m *Manager) Enabled() bool {
	return m != nil && m.cfg.Enabled
}

func (m *Manager) Info() map[string]any {
	mode := "disabled"
	ws := m.cfg.Workspace
	if m.Enabled() {
		if m.cfg.ForceMem || ws == "" {
			mode = "mem"
		} else if st, err := os.Stat(ws); err == nil && st.IsDir() {
			mode = "overlay"
		} else {
			mode = "mem" // fallback
		}
	}
	info := map[string]any{
		"enabled":   m.Enabled(),
		"mode":      mode,
		"workspace": ws,
		"timeout_s": m.cfg.ExecTimeout.Seconds(),
		"builtins":  []string{"cat", "ls", "mkdir", "rm", "pwd", "echo"},
		"actions":   m.actions.Stats(),
	}
	return info
}

// OpenSession creates a fresh sandbox for one request.
func (m *Manager) OpenSession() (*Session, error) {
	if !m.Enabled() {
		return nil, fmt.Errorf("gosh disabled")
	}
	if m.cfg.ForceMem || m.cfg.Workspace == "" {
		return NewMemSession(), nil
	}
	s, err := NewOverlaySession(m.cfg.Workspace)
	if err != nil {
		// Docker-friendly fallback: mem if volume missing
		return NewMemSession(), nil
	}
	return s, nil
}

// RunRequest seeds files/tools, runs script and/or Go source, returns results.
type RunRequest struct {
	Script         string            `json:"script"`
	Source         string            `json:"source"` // Yaegi package main
	Files          map[string]string `json:"files"`
	Tools          []ToolDef         `json:"tools"`
	Read           []string          `json:"read"` // paths to return after run
	ExpectedResult string            `json:"expected_result,omitempty"`
	SessionID      string            `json:"session_id,omitempty"`  // groups lessons; also X-Session-ID
	SkipVerify     bool              `json:"skip_verify,omitempty"` // tests only — default always verify
	StrictTool     bool              `json:"strict_tool,omitempty"` // full JIT tool contract on script
}

type ToolDef struct {
	Name   string `json:"name"`
	Source string `json:"source"`
}

type RunResult struct {
	Mode       string              `json:"mode"`
	Workspace  string              `json:"workspace,omitempty"`
	Stdout     string              `json:"stdout,omitempty"`
	Stderr     string              `json:"stderr,omitempty"`
	ExitOK     bool                `json:"ok"`
	Error      string              `json:"error,omitempty"`
	Files      map[string]string   `json:"files,omitempty"`
	DurationMs int64               `json:"duration_ms"`
	Action     *ActionContext      `json:"action,omitempty"`
	Lessons    string              `json:"lessons,omitempty"`
	Verify     *forge.VerifyResult `json:"verify,omitempty"`
}

func (m *Manager) Run(parent context.Context, req RunRequest) (out RunResult) {
	start := time.Now()
	out.ExitOK = false
	// Named return so defer can attach DurationMs / Action / Lessons after early returns.
	defer func() {
		out.DurationMs = time.Since(start).Milliseconds()
		if m.Enabled() {
			m.recordAction(&out, req)
		}
	}()
	if !m.Enabled() {
		out.Error = "gosh disabled"
		return out
	}
	if !req.SkipVerify {
		toolSrcs := make([]string, 0, len(req.Tools))
		for _, t := range req.Tools {
			toolSrcs = append(toolSrcs, t.Source)
		}
		vr := forge.VerifyStatic(forge.VerifyRequest{
			Script:      req.Script,
			Source:      req.Source,
			ToolSources: toolSrcs,
			StrictTool:  req.StrictTool,
		})
		out.Verify = &vr
		if !vr.OK {
			out.Error = "constitution: " + vr.Summary
			return out
		}
	}
	sess, err := m.OpenSession()
	if err != nil {
		out.Error = err.Error()
		return out
	}
	out.Mode = sess.Mode()
	out.Workspace = sess.Workspace()

	ctx, cancel := context.WithTimeout(parent, m.cfg.ExecTimeout)
	defer cancel()

	for path, content := range req.Files {
		if err := sess.WriteFile(path, []byte(content)); err != nil {
			out.Error = "write " + path + ": " + err.Error()
			return out
		}
	}
	for _, tool := range req.Tools {
		if err := sess.RegisterTool(tool.Name, tool.Source); err != nil {
			out.Error = "tool " + tool.Name + ": " + err.Error()
			return out
		}
	}

	if strings.TrimSpace(req.Script) != "" {
		stdout, err := sess.Execute(ctx, req.Script)
		out.Stdout = stdout
		if err != nil {
			out.Error = err.Error()
			return out
		}
	}
	if strings.TrimSpace(req.Source) != "" {
		stdout, stderr, err := sess.RunGoSource(ctx, req.Source)
		out.Stdout += stdout
		out.Stderr = stderr
		if err != nil {
			out.Error = err.Error()
			return out
		}
	}

	if len(req.Read) > 0 {
		out.Files = make(map[string]string, len(req.Read))
		for _, path := range req.Read {
			data, err := sess.ReadFile(path)
			if err != nil {
				out.Error = "read " + path + ": " + err.Error()
				return out
			}
			out.Files[path] = string(data)
		}
	}

	out.ExitOK = true
	return out
}

func (m *Manager) recordAction(out *RunResult, req RunRequest) {
	if m == nil || m.actions == nil || out == nil {
		return
	}
	actionLabel := strings.TrimSpace(req.Script)
	if actionLabel == "" {
		actionLabel = strings.TrimSpace(req.Source)
	}
	if actionLabel == "" && len(req.Tools) > 0 {
		actionLabel = "tools:" + req.Tools[0].Name
	}
	if actionLabel == "" {
		actionLabel = "gosh.run"
	}
	actual := strings.TrimSpace(out.Stdout)
	if actual == "" && out.Error != "" {
		actual = out.Error
	}
	mismatch, correction := InferMismatch(req.ExpectedResult, actual, out.ExitOK, out.Error)
	ctx := ActionContext{
		LastAction:     clip(actionLabel, 200),
		ExpectedResult: req.ExpectedResult,
		ActualResult:   actual,
		Mismatch:       mismatch,
		CorrectionPlan: correction,
		ConversationID: strings.TrimSpace(req.SessionID),
		OK:             out.ExitOK && mismatch == "",
	}
	m.actions.Record(ctx)
	cp := ctx
	out.Action = &cp
	out.Lessons = m.actions.FormatForPrompt(req.SessionID)
}

// LessonsFor returns the prompt block for a session (empty if none).
func (m *Manager) LessonsFor(sessionID string) string {
	if m == nil || m.actions == nil {
		return ""
	}
	return m.actions.FormatForPrompt(sessionID)
}
