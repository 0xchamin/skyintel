/* settings.js — BYOK settings modal (localStorage, never server-side) */

const PROVIDERS = {
    anthropic: { name: "Claude (Anthropic)", prefix: "anthropic/" },
    openai: { name: "OpenAI", prefix: "" },
    google: { name: "Gemini (Google)", prefix: "gemini/" },
};

const DEFAULT_MODELS = {
    anthropic: "claude-sonnet-4-20250514",
    openai: "gpt-4o",
    google: "gemini-2.0-flash",
};


function getStoredConfig() {
    try {
        return JSON.parse(localStorage.getItem("voyageintel_llm") || "null");
    } catch { return null; }
}


function saveConfig(provider, apiKey, model) {
    localStorage.setItem("voyageintel_llm", JSON.stringify({ provider, apiKey, model }));
}

function clearConfig() {
    localStorage.removeItem("voyageintel_llm");
}

function openSettings() {
    let modal = document.getElementById("settingsModal");
    if (modal) { modal.style.display = "flex"; return; }

    const config = getStoredConfig();

    modal = document.createElement("div");
    modal.id = "settingsModal";
    modal.style.cssText = `
        position:fixed; inset:0; z-index:500;
        display:flex; align-items:center; justify-content:center;
        background:rgba(0,0,0,0.6); backdrop-filter:blur(4px);
    `;
    modal.innerHTML = `
        <div style="background:rgba(20,20,30,0.96); border:1px solid rgba(255,255,255,0.1);
            border-radius:12px; padding:24px; width:380px; color:#fff; font-size:13px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <span style="font-size:16px; font-weight:700; color:#0ff;">⚙ LLM Settings</span>
                <button id="settingsClose" style="background:none; border:none; color:#fff; font-size:18px; cursor:pointer;">✕</button>
            </div>
            <div style="margin-bottom:8px; color:rgba(255,255,255,0.5); font-size:11px;">
                🔒 Your API key is stored in your browser's localStorage only — never sent to our server.
            </div>
            <label style="display:block; margin-bottom:12px;">
                <span style="color:rgba(255,255,255,0.6); display:block; margin-bottom:4px;">Provider</span>
                <select id="llmProvider" style="width:100%; padding:8px; background:rgba(255,255,255,0.08);
                    border:1px solid rgba(255,255,255,0.15); border-radius:6px; color:#fff; font-size:13px;">
                    <option value="anthropic" ${config?.provider === "anthropic" ? "selected" : ""}>Claude (Anthropic)</option>
                    <option value="openai" ${config?.provider === "openai" ? "selected" : ""}>OpenAI</option>
                    <option value="google" ${config?.provider === "google" ? "selected" : ""}>Gemini (Google)</option>
                </select>
            </label>
            <label style="display:block; margin-bottom:12px;">
                <span style="color:rgba(255,255,255,0.6); display:block; margin-bottom:4px;">API Key</span>
                <input id="llmApiKey" type="password" placeholder="sk-... or AIza..."
                    value="${config?.apiKey || ""}"
                    style="width:100%; padding:8px; background:rgba(255,255,255,0.08);
                    border:1px solid rgba(255,255,255,0.15); border-radius:6px; color:#fff; font-size:13px; box-sizing:border-box;" />
            </label>
            <label style="display:block; margin-bottom:16px;">
                <span style="color:rgba(255,255,255,0.6); display:block; margin-bottom:4px;">Model</span>
                <input id="llmModel" type="text" placeholder="e.g. claude-sonnet-4-20250514"
                    value="${config?.model || ""}"
                    style="width:100%; padding:8px; background:rgba(255,255,255,0.08);
                    border:1px solid rgba(255,255,255,0.15); border-radius:6px; color:#fff; font-size:13px; box-sizing:border-box;" />
            </label>
            <div style="display:flex; gap:8px;">
                <button id="settingsSave" style="flex:1; padding:10px; background:rgba(0,255,255,0.15);
                    border:1px solid #0ff; color:#0ff; border-radius:8px; font-weight:600; cursor:pointer;">Save</button>
                <button id="settingsClear" style="flex:1; padding:10px; background:rgba(255,100,100,0.1);
                    border:1px solid rgba(255,100,100,0.3); color:#ef5350; border-radius:8px; font-weight:600; cursor:pointer;">Clear</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    document.getElementById("settingsClose").addEventListener("click", () => modal.style.display = "none");
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.style.display = "none"; });

    document.getElementById("settingsSave").addEventListener("click", () => {
        const provider = document.getElementById("llmProvider").value;
        const apiKey = document.getElementById("llmApiKey").value.trim();
        const model = document.getElementById("llmModel").value.trim();
        if (!apiKey) { alert("API key is required"); return; }
        if (!model) model = DEFAULT_MODELS[provider] || "";
        document.getElementById("llmModel").value = model;
        saveConfig(provider, apiKey, model);
        modal.style.display = "none";
        showShareToast("LLM settings saved!");
    });

    document.getElementById("settingsClear").addEventListener("click", () => {
        clearConfig();
        document.getElementById("llmApiKey").value = "";
        document.getElementById("llmModel").value = "";
        showShareToast("LLM settings cleared.");
    });
}
