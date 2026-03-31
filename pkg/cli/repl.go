package cli

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ── Tea messages ──────────────────────────────────────────────────────────────

type tokenMsg struct{ content string }
type streamDoneMsg struct{}
type streamErrMsg struct{ err error }
type cmdOutputMsg struct{ output string }
type streamStartMsg struct{ ch <-chan StreamToken }

// ── REPL model ────────────────────────────────────────────────────────────────

type Message struct {
	Role    string // "user" | "assistant" | "system"
	Content string
}

type REPLModel struct {
	cfg     *Config
	client  *Client
	history []map[string]string // API message history
	display []Message           // rendered message list

	input     string
	streaming bool
	streamBuf strings.Builder
	width     int
	height    int
	quitting  bool
}

func NewREPLModel(cfg *Config, client *Client) REPLModel {
	return REPLModel{
		cfg:    cfg,
		client: client,
	}
}

// ── Init ──────────────────────────────────────────────────────────────────────

func (m REPLModel) Init() tea.Cmd {
	return nil
}

// ── Update ────────────────────────────────────────────────────────────────────

func (m REPLModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC:
			m.quitting = true
			return m, tea.Quit

		case tea.KeyEnter:
			if m.streaming || strings.TrimSpace(m.input) == "" {
				return m, nil
			}
			return m.submit()

		case tea.KeyBackspace, tea.KeyDelete:
			if len(m.input) > 0 {
				m.input = m.input[:len(m.input)-1]
			}

		case tea.KeyRunes:
			m.input += msg.String()
		}

	case streamStartMsg:
		// Begin pumping tokens — StreamCmd reads one token then re-schedules itself
		return m, StreamCmd(msg.ch)

	case streamContinueMsg:
		// Append token content to streaming buffer and display
		m.streamBuf.WriteString(msg.content)
		if len(m.display) > 0 && m.display[len(m.display)-1].Role == "assistant" {
			m.display[len(m.display)-1].Content = m.streamBuf.String()
		}
		// Schedule next token read
		return m, StreamCmd(msg.ch)

	case tokenMsg:
		m.streamBuf.WriteString(msg.content)
		// Update last assistant message in display in-place
		if len(m.display) > 0 && m.display[len(m.display)-1].Role == "assistant" {
			m.display[len(m.display)-1].Content = m.streamBuf.String()
		}
		return m, nil

	case streamDoneMsg:
		m.streaming = false
		finalContent := m.streamBuf.String()
		// Commit to API history
		m.history = append(m.history, map[string]string{
			"role":    "assistant",
			"content": finalContent,
		})
		m.streamBuf.Reset()
		return m, nil

	case streamErrMsg:
		m.streaming = false
		m.streamBuf.Reset()
		m.display = append(m.display, Message{
			Role:    "system",
			Content: styleDanger.Render("Stream error: " + msg.err.Error()),
		})
		return m, nil

	case cmdOutputMsg:
		m.display = append(m.display, Message{
			Role:    "system",
			Content: msg.output,
		})
		return m, nil
	}

	return m, nil
}

func (m REPLModel) submit() (REPLModel, tea.Cmd) {
	raw := strings.TrimSpace(m.input)
	m.input = ""

	// Slash command
	if strings.HasPrefix(raw, "/") {
		out, handled := handleSlashCommand(raw, m.client, m.cfg, &m.history)
		if handled {
			return m, func() tea.Msg { return cmdOutputMsg{output: out} }
		}
	}

	// Add to display + history
	m.display = append(m.display, Message{Role: "user", Content: raw})
	m.history = append(m.history, map[string]string{"role": "user", "content": raw})

	// Placeholder for streaming response
	m.display = append(m.display, Message{Role: "assistant", Content: ""})
	m.streaming = true

	cfg := m.cfg
	client := m.client
	history := make([]map[string]string, len(m.history))
	copy(history, m.history)

	return m, func() tea.Msg {
		ch, err := client.StreamChat(history, cfg.Model)
		if err != nil {
			return streamErrMsg{err: err}
		}
		// Store channel in a shared slot for the pump to drain
		return streamStartMsg{ch: ch}
	}
}

// ── View ──────────────────────────────────────────────────────────────────────

var (
	styleBanner = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#7C3AED")).
			Bold(true)

	styleUserMsg = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#A78BFA")).
			Bold(true)

	styleAssistantMsg = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#F3F4F6"))

	styleSystemMsg = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#6B7280"))

	styleInputPrompt = lipgloss.NewStyle().
				Foreground(lipgloss.Color("#7C3AED")).
				Bold(true)

	styleCursor = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#A78BFA")).
			Bold(true)
)

func (m REPLModel) View() string {
	if m.quitting {
		return stylePrimary.Render("\nSovereign. Out.\n\n")
	}

	var sb strings.Builder

	// Banner (only when no messages yet)
	if len(m.display) == 0 {
		sb.WriteString(renderBanner())
	}

	// Message history — show last N to fit terminal
	visibleStart := 0
	if len(m.display) > 20 {
		visibleStart = len(m.display) - 20
	}
	for _, msg := range m.display[visibleStart:] {
		sb.WriteString(renderMessage(msg))
	}

	// Input line
	sb.WriteString("\n")
	prefix := styleInputPrompt.Render("▸ ")
	if m.streaming {
		prefix = styleDim.Render("  ")
	}
	cursor := styleCursor.Render("█")
	sb.WriteString(prefix + m.input + cursor + "\n")

	if m.streaming {
		sb.WriteString(styleDim.Render("  generating…") + "\n")
	}

	return sb.String()
}

func renderMessage(msg Message) string {
	switch msg.Role {
	case "user":
		return "\n" + styleUserMsg.Render("you  ") + styleResponse.Render(msg.Content) + "\n"
	case "assistant":
		return "\n" + styleAccent.Render("ori  ") + styleAssistantMsg.Render(msg.Content) + "\n"
	case "system":
		return "\n" + msg.Content + "\n"
	}
	return ""
}

func renderBanner() string {
	lines := []string{
		"",
		styleBanner.Render("  ██████╗ ██████╗ ██╗ ██████╗██╗     ██╗"),
		styleBanner.Render("  ██╔═══██╗██╔══██╗██║██╔════╝██║     ██║"),
		styleBanner.Render("  ██║   ██║██████╔╝██║██║     ██║     ██║"),
		styleBanner.Render("  ██║   ██║██╔══██╗██║██║     ██║     ██║"),
		styleBanner.Render("  ╚██████╔╝██║  ██║██║╚██████╗███████╗██║"),
		styleBanner.Render("   ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝╚══════╝╚═╝"),
		"",
		styleDim.Render("  Sovereign Intelligence — AGLI Phase II"),
		styleDim.Render("  Type to chat · /help for commands · Ctrl+C to exit"),
		"",
	}
	return strings.Join(lines, "\n")
}

// ── Streaming command bridge ──────────────────────────────────────────────────
// StreamCmd is used by the REPL Update loop to pump SSE tokens into bubbletea.
// It reads one token from ch, returns it as a tea.Msg, and re-schedules itself.
// The channel is closed by the SSE parser when the stream ends.
func StreamCmd(ch <-chan StreamToken) tea.Cmd {
	return func() tea.Msg {
		tok, ok := <-ch
		if !ok {
			return streamDoneMsg{}
		}
		if tok.Error != nil {
			return streamErrMsg{err: tok.Error}
		}
		if tok.Done {
			return streamDoneMsg{}
		}
		// Return token AND schedule next read via streamContinueMsg
		return streamContinueMsg{content: tok.Content, ch: ch}
	}
}

type streamContinueMsg struct {
	content string
	ch      <-chan StreamToken
}

// ── Run — full interactive REPL ───────────────────────────────────────────────

// Run starts the bubbletea REPL program.
// This is used by main.go for the interactive mode.
func Run(cfg *Config, client *Client) error {
	m := NewREPLModel(cfg, client)
	p := tea.NewProgram(m, tea.WithAltScreen())
	_, err := p.Run()
	return err
}

// ── One-shot (non-interactive) ────────────────────────────────────────────────

// OneShot sends a single query and streams to stdout directly.
func OneShot(cfg *Config, client *Client, query string) error {
	messages := []map[string]string{{"role": "user", "content": query}}
	ch, err := client.StreamChat(messages, cfg.Model)
	if err != nil {
		// Fallback to blocking
		text, err2 := client.BlockingChat(messages, cfg.Model)
		if err2 != nil {
			return fmt.Errorf("chat failed: %w (stream: %v)", err2, err)
		}
		fmt.Println(styleResponse.Render(text))
		return nil
	}
	fmt.Print(styleAccent.Render("ori  "))
	for tok := range ch {
		if tok.Error != nil {
			return tok.Error
		}
		if tok.Done {
			break
		}
		fmt.Print(tok.Content)
	}
	fmt.Println()
	return nil
}
