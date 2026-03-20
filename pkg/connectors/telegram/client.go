package telegram

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

// --- Pillar 43: Sovereign Telegram Client ---
// Implements direct Go-native communication with the Telegram Bot API.

type Client struct {
	Token  string
	ChatID int64
	BaseURL string
	HTTPClient *http.Client
}

func NewClient(token string, chatID int64) *Client {
	baseURL := os.Getenv("TELEGRAM_LOCAL_SERVER")
	if baseURL == "" {
		baseURL = "https://api.telegram.org"
	}
	
	return &Client{
		Token:   token,
		ChatID:  chatID,
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// SendNotification sends a message to the primary Telegram ChatID.
func (c *Client) SendNotification(text string) error {
	return c.SendMessage(c.ChatID, text, "HTML")
}

// SendMessage sends a text message to a specific chat.
func (c *Client) SendMessage(chatID int64, text string, parseMode string) error {
	if c.Token == "" {
		return fmt.Errorf("telegram token missing")
	}

	reqBody := SendMessageRequest{
		ChatID:    chatID,
		Text:      text,
		ParseMode: parseMode,
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return err
	}

	url := fmt.Sprintf("%s/bot%s/sendMessage", c.BaseURL, c.Token)
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("telegram API error: %d - %s", resp.StatusCode, string(body))
	}

	return nil
}

// SetWebhook configures the Telegram webhook endpoint.
func (c *Client) SetWebhook(webhookURL string) error {
	url := fmt.Sprintf("%s/bot%s/setWebhook?url=%s", c.BaseURL, c.Token, webhookURL)
	resp, err := c.HTTPClient.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to set webhook: %d - %s", resp.StatusCode, string(body))
	}

	return nil
}
