// Main Mavaia Chat Application

(() => {
  const els = {
    // Navigation
    tabs: document.querySelectorAll(".tab"),
    panels: document.querySelectorAll(".panel"),

    // Chat elements
    messages: document.getElementById("messages"),
    input: document.getElementById("user-input"),
    send: document.getElementById("send-btn"),
    stop: document.getElementById("stop-btn"),
    retry: document.getElementById("retry-btn"),
    errorBox: document.getElementById("error-box"),
    errorText: document.getElementById("error-text"),
    errorDismiss: document.getElementById("error-dismiss"),
    status: document.getElementById("status-text"),
    connectionStatus: document.getElementById("connection-status"),

    // File handling
    fileInput: document.getElementById("file-input"),
    attachBtn: document.getElementById("attach-btn"),
    attachments: document.getElementById("attachment-previews"),

    // Settings
    model: document.getElementById("model"),
    temperature: document.getElementById("temperature"),
    tempValue: document.getElementById("temp-value"),
    systemPrompt: document.getElementById("system-prompt"),
    themeToggle: document.getElementById("theme-toggle"),
    themeIcon: document.getElementById("theme-icon"),

    // Threads
    threadList: document.getElementById("thread-list"),
    newThread: document.getElementById("new-thread"),

    // Settings section
    settingsToggle: document.getElementById("settings-toggle"),
    settingsContent: document.getElementById("settings-content"),
    settingsSection: document.getElementById("settings-section"),
  };

  const defaultSettings = {
    endpoint: window.location.origin + "/chat",
    modelsEndpoint: window.location.origin + "/models",
    temperature: 0.7,
    model: "mavaia-cognitive",
    systemPrompt: "You are Mavaia, a precise and helpful cognitive AI. Keep responses concise, and show reasoning only when asked.",
    theme: "light",
  };

  const state = {
    threads: [],
    currentThreadId: null,
    pendingAttachments: [],
    abortController: null,
    lastPayload: null,
    models: [],
    autoScroll: true,
    settings: loadSettings(),
    activeTab: "chat",
  };

  // Initialize
  function init() {
    // Clear any existing errors on startup
    clearError();
    
    loadThreads();
    ensureThread();
    renderThreads();
    applySettingsToUI();
    hydrateModels();
    fetchModels();
    renderMessages();
    renderAttachmentPreviews();
    attachEvents();
    setupTabs();
    checkConnection();
    setStatus("Ready");
  }

  // Settings management
  function loadSettings() {
    try {
      const stored = localStorage.getItem("mavaia.settings");
      return stored ? { ...defaultSettings, ...JSON.parse(stored) } : { ...defaultSettings };
    } catch {
      return { ...defaultSettings };
    }
  }

  function saveSettings() {
    localStorage.setItem("mavaia.settings", JSON.stringify(state.settings));
  }

  function applySettingsToUI() {
    els.temperature.value = state.settings.temperature;
    els.tempValue.textContent = state.settings.temperature.toFixed(1);
    els.systemPrompt.value = state.settings.systemPrompt;
    updateTheme();
  }

  // Theme management
  function updateTheme() {
    document.documentElement.setAttribute("data-theme", state.settings.theme);
    els.themeIcon.textContent = state.settings.theme === "light" ? "🌙" : "☀️";
  }

  // Thread management
  function saveThreads() {
    localStorage.setItem("mavaia.threads", JSON.stringify(state.threads));
    localStorage.setItem("mavaia.currentThreadId", state.currentThreadId || "");
  }

  function loadThreads() {
    try {
      const raw = localStorage.getItem("mavaia.threads");
      const current = localStorage.getItem("mavaia.currentThreadId");
      state.threads = raw ? JSON.parse(raw) : [];
      state.currentThreadId = current || (state.threads[0]?.id ?? null);
    } catch {
      state.threads = [];
      state.currentThreadId = null;
    }
  }

  function ensureThread() {
    if (!state.currentThreadId) {
      const id = crypto.randomUUID();
      const thread = { id, title: "New conversation", messages: [], createdAt: Date.now() };
      state.threads.unshift(thread);
      state.currentThreadId = id;
      saveThreads();
    }
  }

  function currentThread() {
    return state.threads.find((t) => t.id === state.currentThreadId);
  }

  function renderThreads() {
    els.threadList.innerHTML = "";
    state.threads.forEach((t) => {
      const item = document.createElement("div");
      item.className = `thread-item ${t.id === state.currentThreadId ? "active" : ""}`;
      item.textContent = t.title || "Untitled";
      item.onclick = () => {
        state.currentThreadId = t.id;
        saveThreads();
        renderThreads();
        renderMessages();
      };
      item.ondblclick = () => {
        const title = prompt("Rename conversation", t.title || "Untitled");
        if (title !== null && title.trim()) {
          t.title = title.trim();
          saveThreads();
          renderThreads();
        }
      };
      els.threadList.appendChild(item);
    });
  }

  // Tab navigation
  function setupTabs() {
    const savedTab = localStorage.getItem("mavaia.activeTab") || "chat";
    switchTab(savedTab);

    els.tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const tabName = tab.dataset.tab;
        switchTab(tabName);
      });
    });
  }

  function switchTab(tabName) {
    state.activeTab = tabName;
    localStorage.setItem("mavaia.activeTab", tabName);

    els.tabs.forEach((tab) => {
      if (tab.dataset.tab === tabName) {
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");
      } else {
        tab.classList.remove("active");
        tab.setAttribute("aria-selected", "false");
      }
    });

    els.panels.forEach((panel) => {
      if (panel.id === `${tabName}-panel`) {
        panel.classList.add("active");
      } else {
        panel.classList.remove("active");
      }
    });
  }

  // Connection status
  async function checkConnection() {
    try {
      const res = await fetch("/health");
      const data = await res.json();
      if (data.api_connected) {
        els.connectionStatus.classList.remove("disconnected");
      } else {
        els.connectionStatus.classList.add("disconnected");
      }
    } catch {
      els.connectionStatus.classList.add("disconnected");
    }
  }

  // Models
  function hydrateModels() {
    els.model.innerHTML = "";
    state.models.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.id;
      if (m.id === state.settings.model) opt.selected = true;
      els.model.appendChild(opt);
    });
  }

  async function fetchModels() {
    try {
      const res = await fetch(state.settings.modelsEndpoint);
      const data = await res.json();
      state.models = data.data || [];
      if (!state.settings.model && state.models[0]) {
        state.settings.model = state.models[0].id;
        saveSettings();
      }
      hydrateModels();
    } catch (err) {
      console.warn("Model fetch failed", err);
    }
  }

  // Attachments
  function attachmentChip(att) {
    const chip = document.createElement("div");
    chip.className = "attachment-chip";
    chip.innerHTML = `
      <span>${att.name}</span>
      <span style="color: var(--text-tertiary);">(${Utils.formatFileSize(att.size)})</span>
      <button onclick="this.parentElement.remove()" aria-label="Remove attachment">×</button>
    `;
    return chip;
  }

  function renderAttachmentPreviews() {
    els.attachments.innerHTML = "";
    state.pendingAttachments.forEach((att, idx) => {
      const chip = attachmentChip(att);
      chip.querySelector("button").onclick = () => {
        state.pendingAttachments.splice(idx, 1);
        renderAttachmentPreviews();
      };
      els.attachments.appendChild(chip);
    });
  }

  // Messages
  function renderMessages() {
    const thread = currentThread();
    if (!thread) return;
    els.messages.innerHTML = "";

    if (thread.messages.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "Start a conversation with Mavaia...";
      els.messages.appendChild(empty);
      return;
    }

    thread.messages.forEach((m, idx) => {
      const div = document.createElement("div");
      div.className = `message ${m.role}`;

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.innerHTML = `
        <span class="pill">${m.role}</span>
        ${m.createdAt ? `<span>${Utils.formatTime(m.createdAt)}</span>` : ""}
      `;
      div.appendChild(meta);

      const content = document.createElement("div");
      content.className = "content";
      if (m.state === "streaming" || m.state === "pending") {
        content.innerHTML = Utils.renderMarkdown(m.text || "⋯");
        if (m.state === "streaming") {
          content.innerHTML += '<span class="typing-indicator">▊</span>';
        }
      } else {
        content.innerHTML = Utils.renderMarkdown(m.text || "");
      }
      div.appendChild(content);

      if (m.attachments?.length) {
        const wrap = document.createElement("div");
        wrap.style.marginTop = "8px";
        m.attachments.forEach((att) => wrap.appendChild(attachmentChip(att)));
        div.appendChild(wrap);
      }

      const actions = document.createElement("div");
      actions.className = "message-actions";
      if (m.role === "assistant" && m.state === "complete") {
        const copyBtn = document.createElement("button");
        copyBtn.className = "ghost";
        copyBtn.textContent = "Copy";
        copyBtn.onclick = () => Utils.copyToClipboard(m.text);
        actions.appendChild(copyBtn);
      }
      if (m.role === "user") {
        const editBtn = document.createElement("button");
        editBtn.className = "ghost";
        editBtn.textContent = "Edit";
        editBtn.onclick = () => editAndResend(idx);
        actions.appendChild(editBtn);
      }
      div.appendChild(actions);

      els.messages.appendChild(div);
    });

    if (state.autoScroll) {
      setTimeout(() => {
        els.messages.scrollTop = els.messages.scrollHeight;
      }, 100);
    }
  }

  // Status and errors
  function setStatus(text) {
    els.status.textContent = text;
  }

  function showError(msg) {
    if (!msg || msg.trim() === "") {
      // Don't show empty errors
      clearError();
      return;
    }
    els.errorText.textContent = msg;
    els.errorBox.classList.remove("hidden");
    // Scroll error into view
    els.errorBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function clearError() {
    els.errorBox.classList.add("hidden");
    els.errorText.textContent = "";
  }

  // Payload building
  function buildPayload(userText, thread) {
    const messages = [...(thread.messages || [])]
      .filter((m) => m.state === "complete")
      .map((m) => {
        const content = [{ type: "text", text: m.text || "" }];
        if (m.attachments?.length) {
          m.attachments.forEach((att) => {
            if (att.isImage) {
              content.push({ type: "image_url", image_url: { url: att.data } });
            } else {
              content.push({
                type: "input_file",
                file: { name: att.name, data: att.data, mime: att.type },
              });
            }
          });
        }
        return { role: m.role, content };
      });

    messages.push({
      role: "user",
      content: [{ type: "text", text: userText }],
    });

    if (state.pendingAttachments.length) {
      state.pendingAttachments.forEach((att) => {
        if (att.isImage) {
          messages[messages.length - 1].content.push({
            type: "image_url",
            image_url: { url: att.data },
          });
        } else {
          messages[messages.length - 1].content.push({
            type: "input_file",
            file: { name: att.name, data: att.data, mime: att.type },
          });
        }
      });
    }

    return {
      model: state.settings.model,
      temperature: Number(state.settings.temperature),
      messages,
      stream: true,
      system: state.settings.systemPrompt || undefined,
    };
  }

  // Message management
  function pushMessage(role, text, opts = {}) {
    const thread = currentThread();
    if (!thread) return null;
    const msg = {
      id: crypto.randomUUID(),
      role,
      text,
      state: opts.state || "complete",
      attachments: opts.attachments || [],
      createdAt: Date.now(),
    };
    thread.messages.push(msg);
    
    // Update thread title from first user message
    if (role === "user" && thread.messages.length === 1) {
      thread.title = Utils.generateThreadTitle(text);
    }
    
    saveThreads();
    renderMessages();
    return msg;
  }

  function updateMessage(msg, delta) {
    if (!msg) return;
    if (delta.text !== undefined) msg.text = delta.text;
    if (delta.state !== undefined) msg.state = delta.state;
    saveThreads();
    renderMessages();
  }

  // Streaming
  function stopGeneration() {
    if (state.abortController) {
      state.abortController.abort();
      state.abortController = null;
      setStatus("Stopped");
      els.stop.classList.add("hidden");
    }
  }

  async function streamResponse(payload, assistantMsg) {
    state.abortController = new AbortController();
    setStatus("Streaming...");
    els.stop.classList.remove("hidden");
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      const res = await fetch(state.settings.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: state.abortController.signal,
      });

      if (!res.ok) {
        const errBody = await res.text();
        let errorMsg = `Error ${res.status}`;
        try {
          const errData = JSON.parse(errBody);
          errorMsg = errData.error?.message || errorMsg;
        } catch {
          errorMsg = errBody || errorMsg;
        }
        throw new Error(errorMsg);
      }

      const reader = res.body.getReader();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const dataStr = line.replace(/^data:\s?/, "");
          if (dataStr === "[DONE]") {
            updateMessage(assistantMsg, { state: "complete" });
            setStatus("Ready");
            els.stop.classList.add("hidden");
            return;
          }
          try {
            const parsed = JSON.parse(dataStr);
            let delta = "";
            const choice = parsed.choices?.[0];
            if (choice?.delta) {
              // Handle both string and array content formats
              const content = choice.delta.content;
              if (typeof content === "string") {
                delta = content;
              } else if (Array.isArray(content)) {
                delta = content.map((c) => (typeof c === "string" ? c : c.text || "")).join("");
              }
            }
            if (delta) {
              updateMessage(assistantMsg, {
                text: (assistantMsg.text || "") + delta,
                state: "streaming",
              });
            }
          } catch (err) {
            console.warn("Parse chunk failed", err, dataStr);
          }
        }
      }
      updateMessage(assistantMsg, { state: "complete" });
      setStatus("Ready");
    } catch (err) {
      if (err.name === "AbortError") {
        updateMessage(assistantMsg, { state: "complete" });
        setStatus("Stopped");
      } else {
        updateMessage(assistantMsg, { state: "error" });
        showError(err.message || "Stream failed");
        setStatus("Error");
      }
    } finally {
      state.abortController = null;
      els.stop.classList.add("hidden");
    }
  }

  // Actions
  async function sendMessage() {
    clearError();
    ensureThread();
    const text = els.input.value.trim();
    if (!text && state.pendingAttachments.length === 0) return;

    const thread = currentThread();
    const userMsg = pushMessage("user", text || "[Attachment only]", {
      state: "complete",
      attachments: state.pendingAttachments.map((a) => ({ ...a })),
    });
    const assistantMsg = pushMessage("assistant", "", { state: "pending" });
    const payload = buildPayload(text || "", thread);
    state.lastPayload = payload;
    state.pendingAttachments = [];
    renderAttachmentPreviews();
    els.input.value = "";
    els.input.style.height = "auto";
    await streamResponse(payload, assistantMsg);
    saveThreads();
  }

  async function retryLast() {
    clearError();
    if (!state.lastPayload) return;
    const thread = currentThread();
    if (!thread) return;
    // Remove last assistant message if exists
    if (thread.messages.length > 0 && thread.messages[thread.messages.length - 1].role === "assistant") {
      thread.messages.pop();
    }
    const assistantMsg = pushMessage("assistant", "", { state: "pending" });
    await streamResponse(state.lastPayload, assistantMsg);
  }

  async function editAndResend(msgIndex) {
    const thread = currentThread();
    if (!thread) return;
    const msg = thread.messages[msgIndex];
    if (!msg) return;
    const text = prompt("Edit message", msg.text);
    if (text === null) return;
    // Remove messages after this one
    thread.messages = thread.messages.slice(0, msgIndex + 1);
    msg.text = text;
    saveThreads();
    renderMessages();
    els.input.value = text;
    await sendMessage();
  }

  // File handling
  function handleFileInput(evt) {
    const files = Array.from(evt.target.files || []);
    const limit = 5 * 1024 * 1024;
    files.forEach((file) => {
      if (file.size > limit) {
        Utils.showToast(`File ${file.name} exceeds 5MB limit`, "error");
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        state.pendingAttachments.push({
          name: file.name,
          size: file.size,
          type: file.type,
          data: dataUrl,
          isImage: file.type.startsWith("image/"),
        });
        renderAttachmentPreviews();
      };
      reader.readAsDataURL(file);
    });
    evt.target.value = "";
  }

  // Auto-resize textarea
  function autoResizeTextarea() {
    els.input.style.height = "auto";
    els.input.style.height = `${Math.min(els.input.scrollHeight, 200)}px`;
  }

  // Event handlers
  function attachEvents() {
    els.send.onclick = sendMessage;
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    els.input.addEventListener("input", autoResizeTextarea);
    els.retry.onclick = retryLast;
    els.stop.onclick = stopGeneration;
    els.errorDismiss.onclick = clearError;
    els.fileInput.onchange = handleFileInput;
    els.attachBtn.onclick = () => els.fileInput.click();

    els.themeToggle.onclick = () => {
      state.settings.theme = state.settings.theme === "light" ? "dark" : "light";
      updateTheme();
      saveSettings();
    };

    els.temperature.oninput = (e) => {
      const val = Number(e.target.value);
      state.settings.temperature = val;
      els.tempValue.textContent = val.toFixed(1);
      saveSettings();
    };

    els.systemPrompt.oninput = (e) => {
      state.settings.systemPrompt = e.target.value;
      saveSettings();
    };

    els.model.onchange = (e) => {
      state.settings.model = e.target.value;
      saveSettings();
    };

    els.newThread.onclick = () => {
      const id = crypto.randomUUID();
      state.threads.unshift({ id, title: "New conversation", messages: [], createdAt: Date.now() });
      state.currentThreadId = id;
      saveThreads();
      renderThreads();
      renderMessages();
    };

    els.settingsToggle.onclick = () => {
      els.settingsSection.classList.toggle("expanded");
    };

    els.messages.addEventListener("scroll", () => {
      const nearBottom =
        els.messages.scrollTop + els.messages.clientHeight >= els.messages.scrollHeight - 60;
      state.autoScroll = nearBottom;
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if (e.metaKey || e.ctrlKey) {
        if (e.key === "k") {
          e.preventDefault();
          els.newThread.click();
        }
      }
    });

    window.addEventListener("beforeunload", () => {
      stopGeneration();
    });

    // Check connection periodically
    setInterval(checkConnection, 30000);
  }

  // Start app
  init();
})();
