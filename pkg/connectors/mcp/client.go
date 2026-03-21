package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"sync/atomic"
)

// Client implements a Model Context Protocol (MCP) client using stdio transport.
type Client struct {
	Command string
	Args    []string
	cmd     *exec.Cmd
	stdin   io.WriteCloser
	stdout  io.ReadCloser
	
	requestID int64
	pending   map[int64]chan *Response
	mu        sync.Mutex
	
	OnNotification func(method string, params json.RawMessage)
}

func NewClient(command string, args []string) *Client {
	return &Client{
		Command: command,
		Args:    args,
		pending: make(map[int64]chan *Response),
	}
}

// Start spawns the MCP server process and begins the IO loops.
func (c *Client) Start() error {
	c.cmd = exec.Command(c.Command, c.Args...)
	
	stdin, err := c.cmd.StdinPipe()
	if err != nil {
		return err
	}
	c.stdin = stdin

	stdout, err := c.cmd.StdoutPipe()
	if err != nil {
		return err
	}
	c.stdout = stdout

	if err := c.cmd.Start(); err != nil {
		return err
	}

	go c.readLoop()
	return nil
}

func (c *Client) Stop() error {
	if c.stdin != nil {
		c.stdin.Close()
	}
	if c.cmd != nil {
		return c.cmd.Process.Kill()
	}
	return nil
}

func (c *Client) readLoop() {
	scanner := bufio.NewScanner(c.stdout)
	for scanner.Scan() {
		line := scanner.Bytes()
		
		// Attempt to parse as Response
		var resp Response
		if err := json.Unmarshal(line, &resp); err == nil && resp.ID != nil {
			var id int64
			// ID can be int or string in JSON-RPC
			idVal, ok := resp.ID.(float64)
			if ok {
				id = int64(idVal)
			}
			
			c.mu.Lock()
			ch, ok := c.pending[id]
			if ok {
				ch <- &resp
				delete(c.pending, id)
			}
			c.mu.Unlock()
			continue
		}

		// Attempt to parse as Notification
		var note Notification
		if err := json.Unmarshal(line, &note); err == nil && note.Method != "" {
			if c.OnNotification != nil {
				c.OnNotification(note.Method, note.Params)
			}
			continue
		}
	}
}

func (c *Client) Call(ctx context.Context, method string, params interface{}) (json.RawMessage, error) {
	id := atomic.AddInt64(&c.requestID, 1)
	
	paramBytes, err := json.Marshal(params)
	if err != nil {
		return nil, err
	}

	req := Request{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  paramBytes,
	}

	reqBytes, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	ch := make(chan *Response, 1)
	c.mu.Lock()
	c.pending[id] = ch
	c.mu.Unlock()

	// Write to stdin
	if _, err := fmt.Fprintln(c.stdin, string(reqBytes)); err != nil {
		return nil, err
	}

	select {
	case <-ctx.Done():
		c.mu.Lock()
		delete(c.pending, id)
		c.mu.Unlock()
		return nil, ctx.Err()
	case resp := <-ch:
		if resp.Error != nil {
			return nil, fmt.Errorf("RPC Error (%d): %s", resp.Error.Code, resp.Error.Message)
		}
		return resp.Result, nil
	}
}

// Initialize performs the MCP handshake.
func (c *Client) Initialize(ctx context.Context) (*InitializeResult, error) {
	params := InitializeRequest{
		ProtocolVersion: "2024-11-05",
		Capabilities:    make(map[string]interface{}),
		ClientInfo: ImplementationInfo{
			Name:    "Oricli-Alpha",
			Version: "2.10.0",
		},
	}

	resBytes, err := c.Call(ctx, "initialize", params)
	if err != nil {
		return nil, err
	}

	var result InitializeResult
	if err := json.Unmarshal(resBytes, &result); err != nil {
		return nil, err
	}

	// Send initialized notification
	note := Notification{
		JSONRPC: "2.0",
		Method:  "notifications/initialized",
	}
	noteBytes, _ := json.Marshal(note)
	fmt.Fprintln(c.stdin, string(noteBytes))

	return &result, nil
}

// ListTools fetches available tools from the server.
func (c *Client) ListTools(ctx context.Context) ([]MCPTool, error) {
	resBytes, err := c.Call(ctx, "tools/list", map[string]interface{}{})
	if err != nil {
		return nil, err
	}

	var result ListToolsResult
	if err := json.Unmarshal(resBytes, &result); err != nil {
		return nil, err
	}

	return result.Tools, nil
}

// CallTool invokes a specific tool.
func (c *Client) CallTool(ctx context.Context, name string, args map[string]interface{}) (*CallToolResult, error) {
	params := CallToolRequest{
		Name:      name,
		Arguments: args,
	}

	resBytes, err := c.Call(ctx, "tools/call", params)
	if err != nil {
		return nil, err
	}

	var result CallToolResult
	if err := json.Unmarshal(resBytes, &result); err != nil {
		return nil, err
	}

	return &result, nil
}
