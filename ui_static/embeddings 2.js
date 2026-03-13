// Embeddings Testing Interface

(() => {
  const els = {
    embeddingsInput: document.getElementById("embeddings-input"),
    embeddingsBatch: document.getElementById("embeddings-batch"),
    embeddingsExecute: document.getElementById("embeddings-execute"),
    embeddingsClear: document.getElementById("embeddings-clear"),
    embeddingsResults: document.getElementById("embeddings-results"),
  };

  const state = {
    results: null,
  };

  function init() {
    attachEvents();
  }

  async function generateEmbeddings() {
    const input = els.embeddingsInput.value.trim();
    if (!input) {
      Utils.showToast("Please enter text to embed", "error");
      return;
    }

    try {
      els.embeddingsExecute.disabled = true;
      els.embeddingsExecute.textContent = "Generating...";
      els.embeddingsResults.textContent = "Loading...";

      const isBatch = els.embeddingsBatch.checked;
      const inputData = isBatch
        ? input.split("\n").filter((line) => line.trim())
        : input;

      const response = await fetch("/embeddings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: inputData,
          model: "oricli-embeddings",
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || "Embedding generation failed");
      }

      const data = await response.json();
      state.results = {
        input: inputData,
        embeddings: data.data || [],
        usage: data.usage || {},
        model: data.model || "oricli-embeddings",
        timestamp: new Date().toISOString(),
      };

      displayResults();
      Utils.showToast("Embeddings generated successfully", "success");
    } catch (err) {
      Utils.showToast(err.message || "Generation failed", "error");
      els.embeddingsResults.textContent = `Error: ${err.message}`;
    } finally {
      els.embeddingsExecute.disabled = false;
      els.embeddingsExecute.textContent = "Generate Embeddings";
    }
  }

  function displayResults() {
    if (!state.results) return;

    const resultDiv = document.createElement("div");
    
    const embeddings = state.results.embeddings;
    const isMultiple = Array.isArray(state.results.input) && state.results.input.length > 1;

    let html = `
      <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
        <strong>Model:</strong> ${state.results.model}<br>
        <strong>Input Count:</strong> ${isMultiple ? state.results.input.length : 1}<br>
        <strong>Embedding Dimensions:</strong> ${embeddings[0]?.embedding?.length || "N/A"}<br>
        <strong>Timestamp:</strong> ${new Date(state.results.timestamp).toLocaleString()}
      </div>
    `;

    if (state.results.usage) {
      html += `
        <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
          <strong>Usage:</strong><br>
          <pre style="background: var(--bg-tertiary); padding: 8px; border-radius: 4px; margin-top: 4px;">${Utils.formatJSON(state.results.usage)}</pre>
        </div>
      `;
    }

    html += `<div style="margin-bottom: 12px;"><strong>Embeddings:</strong></div>`;

    embeddings.forEach((item, idx) => {
      const embedding = item.embedding || [];
      const preview = embedding.slice(0, 10).map((v) => v.toFixed(4)).join(", ");
      const inputText = isMultiple ? state.results.input[idx] : state.results.input;
      const truncatedText = inputText.length > 100 ? inputText.substring(0, 100) + "..." : inputText;

      html += `
        <div style="margin-bottom: 16px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
          <div style="margin-bottom: 8px;">
            <strong>#${idx + 1}</strong>
            ${isMultiple ? `<br><small style="color: var(--text-secondary);">${truncatedText}</small>` : ""}
          </div>
          <div style="margin-bottom: 8px;">
            <strong>Dimensions:</strong> ${embedding.length}<br>
            <strong>Preview (first 10):</strong> [${preview}...]
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="ghost" onclick="copyEmbedding(${idx})" style="font-size: 12px;">Copy Vector</button>
            <button class="ghost" onclick="copyEmbeddingJSON(${idx})" style="font-size: 12px;">Copy JSON</button>
          </div>
          <pre id="embedding-${idx}" style="display: none; margin-top: 8px; background: var(--bg-primary); padding: 8px; border-radius: 4px; overflow-x: auto; max-height: 200px; overflow-y: auto;">${JSON.stringify(embedding, null, 2)}</pre>
        </div>
      `;
    });

    html += `
      <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
        <button class="ghost" onclick="copyAllEmbeddings()" style="font-size: 12px;">Copy All as JSON</button>
      </div>
    `;

    resultDiv.innerHTML = html;
    els.embeddingsResults.innerHTML = "";
    els.embeddingsResults.appendChild(resultDiv);
  }

  function clearEmbeddings() {
    els.embeddingsInput.value = "";
    els.embeddingsBatch.checked = false;
    els.embeddingsResults.innerHTML = "";
    state.results = null;
  }

  // Global functions for copy buttons
  window.copyEmbedding = function (idx) {
    if (!state.results || !state.results.embeddings[idx]) return;
    const embedding = state.results.embeddings[idx].embedding;
    Utils.copyToClipboard(JSON.stringify(embedding));
  };

  window.copyEmbeddingJSON = function (idx) {
    if (!state.results || !state.results.embeddings[idx]) return;
    const item = state.results.embeddings[idx];
    Utils.copyToClipboard(JSON.stringify(item, null, 2));
  };

  window.copyAllEmbeddings = function () {
    if (!state.results) return;
    Utils.copyToClipboard(JSON.stringify(state.results, null, 2));
  };

  function attachEvents() {
    els.embeddingsExecute.onclick = generateEmbeddings;
    els.embeddingsClear.onclick = clearEmbeddings;
    els.embeddingsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        generateEmbeddings();
      }
    });
  }

  // Initialize when embeddings panel is shown
  const embeddingsPanel = document.getElementById("embeddings-panel");
  if (embeddingsPanel) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "attributes" && mutation.attributeName === "class") {
          if (embeddingsPanel.classList.contains("active")) {
            init();
          }
        }
      });
    });
    observer.observe(embeddingsPanel, { attributes: true });
  }

  // Also init immediately if panel is already active
  if (embeddingsPanel?.classList.contains("active")) {
    init();
  }
})();

