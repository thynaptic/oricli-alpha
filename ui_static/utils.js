// Shared utilities for Oricli-Alpha UI

const Utils = {
  // Toast notifications
  showToast(message, type = "info", duration = 3000) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = "slideIn 0.3s ease-out reverse";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  // Format JSON with syntax highlighting
  formatJSON(obj) {
    return JSON.stringify(obj, null, 2);
  },

  // Copy to clipboard
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      this.showToast("Copied to clipboard", "success");
      return true;
    } catch (err) {
      this.showToast("Failed to copy", "error");
      return false;
    }
  },

  // Format file size
  formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  },

  // Debounce function
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Generate thread title from message
  generateThreadTitle(text) {
    const maxLength = 50;
    const trimmed = text.trim();
    if (trimmed.length <= maxLength) return trimmed;
    return trimmed.substring(0, maxLength) + "...";
  },

  // Parse SSE stream
  parseSSE(buffer) {
    const lines = buffer.split("\n\n");
    const events = [];
    let remaining = "";

    for (const line of lines) {
      if (!line.trim()) continue;
      if (line.startsWith("data:")) {
        const data = line.replace(/^data:\s?/, "").trim();
        if (data === "[DONE]") {
          events.push({ done: true });
        } else {
          try {
            events.push({ data: JSON.parse(data) });
          } catch (e) {
            // Invalid JSON, skip
          }
        }
      } else {
        remaining += line + "\n\n";
      }
    }

    return { events, remaining };
  },

  // Simple markdown renderer (basic support)
  renderMarkdown(text) {
    // Escape HTML first
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    return html;
  },

  // Format timestamp
  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  },
};

