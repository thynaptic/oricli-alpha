package api

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

const sharesCollection = "canvas_shares"

// shareBaseURL returns the public base URL for share links.
func shareBaseURL() string {
	if u := os.Getenv("SHARE_BASE_URL"); u != "" {
		return strings.TrimRight(u, "/")
	}
	return "https://oristudio.thynaptic.com"
}

// handleCreateShare saves a canvas document and returns a permanent share URL.
// POST /v1/share
// Body: { "title": "...", "content": "...", "doc_type": "html", "language": "..." }
func (s *ServerV2) handleCreateShare(c *gin.Context) {
	var body struct {
		Title    string `json:"title"`
		Content  string `json:"content"`
		DocType  string `json:"doc_type"`
		Language string `json:"language"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Content == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "content is required"})
		return
	}
	if body.DocType == "" {
		body.DocType = "html"
	}

	shareID := newShareID()

	pbClient := pb.NewClientFromEnv()
	id, err := pbClient.CreateRecord(c.Request.Context(), sharesCollection, map[string]any{
		"share_id": shareID,
		"title":    body.Title,
		"doc_type": body.DocType,
		"content":  body.Content,
		"language": body.Language,
	})
	if err != nil {
		log.Printf("[Share] CreateRecord error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save share"})
		return
	}

	url := fmt.Sprintf("%s/share/%s", shareBaseURL(), shareID)
	log.Printf("[Share] Created share %s (pb_id=%s)", shareID, id)
	c.JSON(http.StatusOK, gin.H{
		"share_id": shareID,
		"url":      url,
	})
}

// handleGetShare serves a shared canvas document publicly.
// GET /share/:id  — no auth required
func (s *ServerV2) handleGetShare(c *gin.Context) {
	shareID := c.Param("id")
	if shareID == "" {
		c.String(http.StatusBadRequest, "missing share id")
		return
	}

	pbClient := pb.NewClientFromEnv()
	resp, err := pbClient.QueryRecords(c.Request.Context(), sharesCollection,
		fmt.Sprintf("share_id = '%s'", shareID), "", 1)
	if err != nil || len(resp.Items) == 0 {
		c.String(http.StatusNotFound, "share not found")
		return
	}

	record := resp.Items[0]
	content, _ := record["content"].(string)
	docType, _ := record["doc_type"].(string)

	if content == "" {
		c.String(http.StatusNotFound, "share is empty")
		return
	}

	switch docType {
	case "html":
		c.Header("Content-Type", "text/html; charset=utf-8")
		c.String(http.StatusOK, content)
	case "markdown":
		// Wrap in a minimal HTML page with readable styling
		title, _ := record["title"].(string)
		if title == "" {
			title = "Shared Document"
		}
		c.Header("Content-Type", "text/html; charset=utf-8")
		c.String(http.StatusOK, markdownSharePage(title, content))
	default:
		// Plain text / code — wrap in a styled code page
		title, _ := record["title"].(string)
		lang, _ := record["language"].(string)
		c.Header("Content-Type", "text/html; charset=utf-8")
		c.String(http.StatusOK, codeSharePage(title, lang, content))
	}
}

// handleListShares returns the most recent shared artifacts.
// GET /v1/shares
func (s *ServerV2) handleListShares(c *gin.Context) {
	pbClient := pb.NewClientFromEnv()
	resp, err := pbClient.QueryRecords(c.Request.Context(), sharesCollection, "", "-created", 30)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	type ShareItem struct {
		ShareID  string `json:"share_id"`
		Title    string `json:"title"`
		DocType  string `json:"doc_type"`
		Language string `json:"language"`
		Created  string `json:"created"`
	}
	shares := make([]ShareItem, 0, len(resp.Items))
	for _, r := range resp.Items {
		shares = append(shares, ShareItem{
			ShareID:  fmt.Sprint(r["share_id"]),
			Title:    fmt.Sprint(r["title"]),
			DocType:  fmt.Sprint(r["doc_type"]),
			Language: fmt.Sprint(r["language"]),
			Created:  fmt.Sprint(r["created"]),
		})
	}
	c.JSON(http.StatusOK, gin.H{"shares": shares, "count": len(shares)})
}

func newShareID() string {
	b := make([]byte, 6) // 12 hex chars — short but collision-resistant enough
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func markdownSharePage(title, content string) string {
	escaped := strings.ReplaceAll(content, "</", "<\\/")
	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 780px; margin: 48px auto; padding: 0 24px;
         color: #e8e3d8; background: #0f0f0f; line-height: 1.7; }
  h1,h2,h3 { color: #E5004C; }
  code { background: #1a1a1a; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre  { background: #1a1a1a; padding: 16px; border-radius: 8px; overflow-x: auto; }
  a    { color: #E5004C; }
  blockquote { border-left: 3px solid #E5004C; margin: 0; padding-left: 16px; color: #999; }
</style>
</head>
<body>
<div id="content"></div>
<script>
  document.getElementById('content').innerHTML = marked.parse(%s);
</script>
</body>
</html>`, title, "`"+escaped+"`")
}

func codeSharePage(title, lang, content string) string {
	if title == "" {
		title = "Shared Code"
	}
	escaped := strings.ReplaceAll(content, "<", "&lt;")
	escaped = strings.ReplaceAll(escaped, ">", "&gt;")
	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<style>
  body { margin: 0; background: #0f0f0f; color: #e8e3d8;
         font-family: "JetBrains Mono", "Fira Code", monospace; }
  .header { padding: 16px 24px; background: #1a1a1a; border-bottom: 1px solid #2a2a2a;
            font-size: 13px; color: #E5004C; display: flex; gap: 12px; align-items: center; }
  .lang   { font-size: 11px; background: rgba(229,0,76,0.1); padding: 2px 8px;
            border-radius: 10px; color: #E5004C; text-transform: uppercase; }
  pre     { margin: 0; padding: 32px 24px; font-size: 14px; line-height: 1.6;
            white-space: pre-wrap; word-break: break-word; }
</style>
</head>
<body>
<div class="header">
  <span>%s</span>
  %s
</div>
<pre>%s</pre>
</body>
</html>`, title, title,
		func() string {
			if lang != "" {
				return fmt.Sprintf(`<span class="lang">%s</span>`, lang)
			}
			return ""
		}(),
		escaped)
}
