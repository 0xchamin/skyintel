/* chat.js — slide-out chat panel with localStorage history */

const CHAT_STORAGE_KEY = "skyintel_chat_history";
const MAX_HISTORY = 50;

function getChatHistory() {
    try {
        return JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || "[]");
    } catch { return []; }
}

function saveChatHistory(messages) {
    const trimmed = messages.slice(-MAX_HISTORY);
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(trimmed));
}

function clearChatHistory() {
    localStorage.removeItem(CHAT_STORAGE_KEY);
}

function initChatPanel() {
    const panel = document.createElement("div");
    panel.id = "chatPanel";
    panel.innerHTML = `
        <div class="chat-header">
            <span class="chat-title">💬 Open Sky Intelligence Chat</span>
            <div style="display:flex; gap:6px;">
                <button id="chatExpand" title="Expand/collapse" style="background:none; border:none; color:rgba(255,255,255,0.5); font-size:16px; cursor:pointer;">⇔</button>
                <button id="chatClear" title="Clear history" style="background:none; border:none; color:rgba(255,255,255,0.5); font-size:16px; cursor:pointer;">🗑</button>
                <button id="chatClose" style="background:rgba(255,255,255,0.1); border:none; color:#fff; font-size:16px; width:28px; height:28px; border-radius:50%; cursor:pointer; display:flex; align-items:center; justify-content:center;">✕</button>
            </div>
        </div>
        <div id="chatMessages"></div>
        <div class="chat-input-area">
            <div id="chatNoKey" style="display:none; padding:8px; color:#ef5350; font-size:12px; text-align:center;">
                ⚠ Set your LLM API key in ⚙ Settings first.
            </div>
            <div style="display:flex; gap:8px;">
                <textarea id="chatInput" placeholder="Ask about flights, satellites, weather…" rows="1"></textarea>
                <button id="chatSend">▶</button>
            </div>
        </div>
    `;
    document.body.appendChild(panel);

    // Styles
    const style = document.createElement("style");
    style.textContent = `
        #chatPanel {
            position: fixed;
            top: 48px; right: 0; bottom: 0;
            width: 400px;
            background: rgba(16, 16, 24, 0.96);
            backdrop-filter: blur(12px);
            border-left: 1px solid rgba(255,255,255,0.1);
            z-index: 180;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        #chatPanel.open { transform: translateX(0); }
        .chat-header {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-title {
            font-size: 15px;
            font-weight: 700;
            color: #0ff;
        }
        #chatMessages {
            flex: 1;
            overflow-y: auto;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        #chatPanel.expanded { width: 700px; }
        .chat-msg {
            max-width: 90%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .chat-msg.user {
            align-self: flex-end;
            background: rgba(0, 255, 255, 0.12);
            border: 1px solid rgba(0, 255, 255, 0.25);
            color: #e0f7fa;
        }
        .chat-msg.assistant {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
        }
        .chat-msg.assistant h1, .chat-msg.assistant h2, .chat-msg.assistant h3 {
            font-size: 14px;
            margin: 8px 0 4px;
            color: #0ff;
        }
        .chat-msg.assistant table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
            font-size: 12px;
        }
        .chat-msg.assistant th, .chat-msg.assistant td {
            border: 1px solid rgba(255,255,255,0.1);
            padding: 4px 8px;
            text-align: left;
        }
        .chat-msg.assistant th {
            background: rgba(0,255,255,0.1);
            color: #0ff;
        }
        .chat-msg.assistant code {
            background: rgba(255,255,255,0.1);
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 12px;
        }
        .chat-msg.assistant pre {
            background: rgba(0,0,0,0.3);
            padding: 8px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
        }
        .chat-msg.assistant ul, .chat-msg.assistant ol {
            padding-left: 18px;
            margin: 4px 0;
        }
        .chat-msg.thinking {
            align-self: flex-start;
            color: rgba(255,255,255,0.4);
            font-style: italic;
            padding: 10px 14px;
            font-size: 13px;
        }
        .chat-msg.error {
            align-self: flex-start;
            background: rgba(255, 80, 80, 0.1);
            border: 1px solid rgba(255, 80, 80, 0.3);
            color: #ef5350;
        }
        .chat-input-area {
            padding: 12px 16px;
            border-top: 1px solid rgba(255,255,255,0.08);
        }
        #chatInput {
            flex: 1;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            color: #fff;
            padding: 10px 12px;
            font-size: 13px;
            resize: none;
            outline: none;
            font-family: inherit;
            min-height: 20px;
            max-height: 100px;
        }
        #chatInput:focus {
            border-color: rgba(0,255,255,0.4);
        }
        #chatInput::placeholder {
            color: rgba(255,255,255,0.3);
        }
        #chatSend {
            background: rgba(0,255,255,0.15);
            border: 1px solid #0ff;
            color: #0ff;
            border-radius: 8px;
            width: 42px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.2s;
        }
        #chatSend:hover { background: rgba(0,255,255,0.25); }
        #chatSend:disabled { opacity: 0.3; cursor: not-allowed; }
    `;
    document.head.appendChild(style);

    // Event listeners
    document.getElementById("chatClose").addEventListener("click", () => {
        panel.classList.remove("open");
    });

    document.getElementById("chatClear").addEventListener("click", () => {
        clearChatHistory();
        document.getElementById("chatMessages").innerHTML = "";
        showShareToast("Chat history cleared.");
    });

    document.getElementById("chatExpand").addEventListener("click", () => {
    panel.classList.toggle("expanded");
    });

    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");

    sendBtn.addEventListener("click", () => sendMessage());
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    input.addEventListener("input", () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });

    // Load history
    renderHistory();
}

function toggleChat() {
    const panel = document.getElementById("chatPanel");
    if (!panel) return;
    panel.classList.toggle("open");

    const config = getStoredConfig();
    const noKey = document.getElementById("chatNoKey");
    if (noKey) {
        noKey.style.display = config?.apiKey ? "none" : "block";
    }
}

function renderHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;
    container.innerHTML = "";
    const history = getChatHistory();
    for (const msg of history) {
        appendMessage(msg.role, msg.content, false);
    }
    container.scrollTop = container.scrollHeight;
}

function appendMessage(role, content, save = true) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;

    if (role === "assistant") {
        div.innerHTML = renderMarkdown(content);
    } else {
        div.textContent = content;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    if (save && (role === "user" || role === "assistant")) {
        const history = getChatHistory();
        history.push({ role, content });
        saveChatHistory(history);
    }

    return div;
}

function removeElement(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSend");
    const text = input.value.trim();
    if (!text) return;

    const config = getStoredConfig();
    if (!config?.apiKey) {
        showShareToast("Set your API key in ⚙ Settings first.");
        return;
    }

    // Show user message
    appendMessage("user", text);
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;

    // Show thinking indicator
    const thinking = appendMessage("thinking", "Thinking…", false);

    try {
        const history = getChatHistory().slice(-6);
        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: history,
                provider: config.provider,
                api_key: config.apiKey,
                model: config.model,
            }),
        });

        removeElement(thinking);

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: "Request failed" }));
            appendMessage("error", `Error: ${err.error || resp.statusText}`, false);
            return;
        }

        const data = await resp.json();
        appendMessage("assistant", data.reply);

    } catch (e) {
        removeElement(thinking);
        appendMessage("error", `Network error: ${e.message}`, false);
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

// Simple markdown → HTML renderer
function renderMarkdown(text) {
    if (!text) return "";

    // HTML passthrough (for reports)
    if (text.trim().startsWith("<") && text.trim().endsWith(">")) {
        return text;
    }

    let html = text
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Unordered lists
        .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
        // Ordered lists
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:#0ff">$1</a>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap loose <li> in <ul>
    html = html.replace(/((?:<li>.*?<\/li>\s*)+)/g, '<ul>$1</ul>');

    return `<p>${html}</p>`;
}
