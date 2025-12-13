// Module Testing Interface

(() => {
  const els = {
    moduleSelect: document.getElementById("module-select"),
    operationSelect: document.getElementById("operation-select"),
    moduleParams: document.getElementById("module-params"),
    moduleExecute: document.getElementById("module-execute"),
    moduleClear: document.getElementById("module-clear"),
    moduleResults: document.getElementById("module-results"),
  };

  const state = {
    modules: [],
    selectedModule: null,
    selectedOperation: null,
    params: {},
    results: null,
  };

  function init() {
    fetchModules();
    attachEvents();
  }

  async function fetchModules() {
    // Show loading state
    els.moduleSelect.innerHTML = '<option value="">Loading modules...</option>';
    els.moduleSelect.disabled = true;
    
    try {
      const res = await fetch("/modules");
      if (!res.ok) {
        const errorText = await res.text();
        let errorMsg = `Failed to load modules (${res.status})`;
        try {
          const errorData = JSON.parse(errorText);
          errorMsg = errorData.error?.message || errorMsg;
        } catch {
          errorMsg = errorText || errorMsg;
        }
        throw new Error(errorMsg);
      }
      const data = await res.json();
      console.log("Modules response:", data);
      state.modules = data.modules || [];
      if (state.modules.length === 0) {
        console.warn("No modules found in response:", data);
        Utils.showToast("No modules available. Make sure the API server is running and modules are loaded.", "info");
      }
      populateModules();
    } catch (err) {
      const errorMsg = err.message || "Failed to load modules";
      Utils.showToast(errorMsg, "error");
      console.error("Error fetching modules:", err);
      els.moduleSelect.innerHTML = `<option value="">Error: ${errorMsg}</option>`;
    } finally {
      els.moduleSelect.disabled = false;
    }
  }

  function populateModules() {
    els.moduleSelect.innerHTML = '<option value="">Select a module...</option>';
    if (state.modules.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No modules available";
      opt.disabled = true;
      els.moduleSelect.appendChild(opt);
      return;
    }
    state.modules.forEach((module) => {
      const opt = document.createElement("option");
      opt.value = module.name;
      opt.textContent = `${module.name} (v${module.version})`;
      opt.dataset.module = JSON.stringify(module);
      els.moduleSelect.appendChild(opt);
    });
  }

  function onModuleSelect() {
    const selected = els.moduleSelect.options[els.moduleSelect.selectedIndex];
    if (!selected || !selected.value) {
      state.selectedModule = null;
      els.operationSelect.disabled = true;
      els.operationSelect.innerHTML = '<option value="">Select a module first</option>';
      els.moduleParams.innerHTML = '<p class="empty-state">Select a module and operation to test</p>';
      els.moduleExecute.disabled = true;
      return;
    }

    const module = JSON.parse(selected.dataset.module);
    state.selectedModule = module;
    populateOperations(module);
  }

  function populateOperations(module) {
    els.operationSelect.disabled = false;
    els.operationSelect.innerHTML = '<option value="">Select an operation...</option>';
    module.operations.forEach((op) => {
      const opt = document.createElement("option");
      opt.value = op;
      opt.textContent = op;
      els.operationSelect.appendChild(opt);
    });
  }

  function onOperationSelect() {
    const operation = els.operationSelect.value;
    state.selectedOperation = operation;
    if (!operation) {
      els.moduleParams.innerHTML = '<p class="empty-state">Select an operation to test</p>';
      els.moduleExecute.disabled = true;
      return;
    }

    renderParamsForm();
    els.moduleExecute.disabled = false;
  }

  function renderParamsForm() {
    els.moduleParams.innerHTML = "";
    
    // Create a simple form for common parameters
    const form = document.createElement("div");
    form.className = "params-form";
    
    // Common parameters
    const commonParams = ["text", "input", "query", "data", "context"];
    
    commonParams.forEach((param) => {
      const label = document.createElement("label");
      label.innerHTML = `
        ${param.charAt(0).toUpperCase() + param.slice(1)}
        <input type="text" id="param-${param}" placeholder="Enter ${param}..." />
      `;
      form.appendChild(label);
    });

    // JSON input for complex parameters
    const jsonLabel = document.createElement("label");
    jsonLabel.innerHTML = `
      Parameters (JSON)
      <textarea id="param-json" rows="6" placeholder='{"key": "value"}'></textarea>
      <small style="color: var(--text-tertiary); font-size: 12px;">Enter JSON object for complex parameters</small>
    `;
    form.appendChild(jsonLabel);

    els.moduleParams.appendChild(form);
  }

  function collectParams() {
    const params = {};
    
    // Collect from individual inputs
    const commonParams = ["text", "input", "query", "data", "context"];
    commonParams.forEach((param) => {
      const input = document.getElementById(`param-${param}`);
      if (input && input.value.trim()) {
        params[param] = input.value.trim();
      }
    });

    // Collect from JSON input
    const jsonInput = document.getElementById("param-json");
    if (jsonInput && jsonInput.value.trim()) {
      try {
        const jsonParams = JSON.parse(jsonInput.value);
        Object.assign(params, jsonParams);
      } catch (e) {
        throw new Error("Invalid JSON in parameters field");
      }
    }

    return params;
  }

  async function executeModule() {
    if (!state.selectedModule || !state.selectedOperation) return;

    try {
      const params = collectParams();
      els.moduleExecute.disabled = true;
      els.moduleExecute.textContent = "Executing...";
      els.moduleResults.textContent = "Loading...";

      // For now, we'll use the chat API to execute modules
      // In a full implementation, you'd have a dedicated module execution endpoint
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "mavaia-cognitive",
          messages: [
            {
              role: "user",
              content: `Execute module ${state.selectedModule.name} with operation ${state.selectedOperation} and parameters: ${JSON.stringify(params)}`,
            },
          ],
          stream: false,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || "Execution failed");
      }

      const data = await response.json();
      const result = data.choices?.[0]?.message?.content || data;

      state.results = {
        module: state.selectedModule.name,
        operation: state.selectedOperation,
        params,
        result: typeof result === "string" ? result : JSON.stringify(result, null, 2),
        timestamp: new Date().toISOString(),
      };

      displayResults();
      Utils.showToast("Module executed successfully", "success");
    } catch (err) {
      Utils.showToast(err.message || "Execution failed", "error");
      els.moduleResults.textContent = `Error: ${err.message}`;
    } finally {
      els.moduleExecute.disabled = false;
      els.moduleExecute.textContent = "Execute";
    }
  }

  function displayResults() {
    if (!state.results) return;

    const resultDiv = document.createElement("div");
    resultDiv.innerHTML = `
      <div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
        <strong>Module:</strong> ${state.results.module}<br>
        <strong>Operation:</strong> ${state.results.operation}<br>
        <strong>Timestamp:</strong> ${new Date(state.results.timestamp).toLocaleString()}
      </div>
      <div style="margin-bottom: 12px;">
        <strong>Parameters:</strong>
        <pre style="background: var(--bg-tertiary); padding: 8px; border-radius: 4px; margin-top: 4px;">${Utils.formatJSON(state.results.params)}</pre>
      </div>
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <strong>Result:</strong>
          <button class="ghost" onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent); Utils.showToast('Copied', 'success');" style="font-size: 12px;">Copy</button>
        </div>
        <pre style="background: var(--bg-tertiary); padding: 12px; border-radius: 4px; overflow-x: auto;">${state.results.result}</pre>
      </div>
    `;

    els.moduleResults.innerHTML = "";
    els.moduleResults.appendChild(resultDiv);
  }

  function clearModule() {
    els.moduleSelect.value = "";
    els.operationSelect.value = "";
    els.operationSelect.disabled = true;
    els.moduleParams.innerHTML = '<p class="empty-state">Select a module and operation to test</p>';
    els.moduleResults.innerHTML = "";
    els.moduleExecute.disabled = true;
    state.selectedModule = null;
    state.selectedOperation = null;
    state.results = null;
  }

  function attachEvents() {
    els.moduleSelect.onchange = onModuleSelect;
    els.operationSelect.onchange = onOperationSelect;
    els.moduleExecute.onclick = executeModule;
    els.moduleClear.onclick = clearModule;
  }

  // Initialize when modules panel is shown
  const modulesPanel = document.getElementById("modules-panel");
  if (modulesPanel) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "attributes" && mutation.attributeName === "class") {
          if (modulesPanel.classList.contains("active") && state.modules.length === 0) {
            init();
          }
        }
      });
    });
    observer.observe(modulesPanel, { attributes: true });
  }

  // Also init immediately if panel is already active
  if (modulesPanel?.classList.contains("active")) {
    init();
  }
})();

