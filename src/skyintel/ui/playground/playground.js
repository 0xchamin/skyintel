/* playground.js — dashboard logic + auto-refresh */

const REFRESH_MS = 15000;
let lastRefresh = null;
let refreshTimer = null;

// ── Helpers ───────────────────────────────────────────────
function fmt(n) {
    if (n === null || n === undefined) return "--";
    return Number(n).toLocaleString();
}

function fmtBytes(bytes) {
    if (bytes === null || bytes === undefined) return "--";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function fmtDuration(seconds) {
    if (seconds === null || seconds === undefined) return "--";
    const s = Math.floor(seconds);
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m " + (s % 60) + "s";
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h < 24) return h + "h " + m + "m";
    const d = Math.floor(h / 24);
    return d + "d " + (h % 24) + "h";
}

function fmtTime(iso) {
    if (!iso) return "--";
    try {
        const d = new Date(iso);
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch { return "--"; }
}

function fmtTimeAgo(iso) {
    if (!iso) return "";
    try {
        const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
        if (secs < 5) return "just now";
        if (secs < 60) return secs + "s ago";
        if (secs < 3600) return Math.floor(secs / 60) + "m ago";
        return Math.floor(secs / 3600) + "h ago";
    } catch { return ""; }
}

function setStatus(el, status, text) {
    el.className = "pg-status " + status;
    el.innerHTML = `<span class="pg-status-dot"></span> ${text}`;
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
}

// ── Fetch System Metrics ──────────────────────────────────
async function fetchSystem() {
    try {
        const resp = await fetch("/api/playground/system");
        if (!resp.ok) throw new Error(resp.status);
        const d = await resp.json();

        // Flights
        const total = (d.flights_commercial || 0) + (d.flights_military || 0) + (d.flights_private || 0);
        setText("flightsTotal", fmt(total));
        setText("flightsSub", `last poll ${fmtTimeAgo(d.last_flight_poll)}`);
        setText("flightsCommercial", fmt(d.flights_commercial));
        setText("flightsMilitary", fmt(d.flights_military));
        setText("flightsPrivate", fmt(d.flights_private));

        // Satellites
        setText("satellitesTotal", fmt(d.satellites_cached));
        setText("satellitesSub", `across ${d.satellite_categories || "--"} categories`);

        // Polling & Uptime
        setText("pollCount", fmt(d.poll_count));
        setText("uptime", fmtDuration(d.uptime_seconds));
        setText("flightInterval", (d.flight_poll_interval || 60) + "s");
        setText("satInterval", (d.satellite_poll_interval || 3600) + "s");

        // Database
        setText("dbSize", fmtBytes(d.db_size_bytes));
        setText("dbPath", d.db_path || "--");

        // Data Sources
        updateSource("srcAdsb", d.sources?.adsb_lol);
        updateSource("srcCelestrak", d.sources?.celestrak);
        updateSource("srcHexdb", d.sources?.hexdb);
        updateSource("srcOpenmeteo", d.sources?.open_meteo);

        // LLM
        setText("llmProvider", d.llm_provider || "not configured");
        setText("llmModel", d.llm_model || "—");
        setText("llmApiKey", d.llm_api_key_set ? "✓ set" : "✗ not set");
        setText("llmLangfuse", d.langfuse_configured ? "✓ configured" : "✗ not set");

    } catch (e) {
        console.error("Failed to fetch system metrics:", e);
    }
}

function updateSource(id, src) {
    const el = document.getElementById(id);
    if (!el || !src) {
        if (el) setStatus(el, "down", "unknown");
        return;
    }
    if (src.healthy) {
        setStatus(el, "healthy", src.last_success ? fmtTimeAgo(src.last_success) : "healthy");
    } else {
        setStatus(el, "down", src.error || "unreachable");
    }
}

// ── Fetch Guardrails ──────────────────────────────────────
async function fetchGuardrails() {
    try {
        const resp = await fetch("/api/playground/guardrails");
        if (!resp.ok) throw new Error(resp.status);
        const d = await resp.json();

        if (!d.available) {
            setText("guardsTotal", "—");
            setText("guardsBlocked", "—");
            setText("guardsBlockRate", "guardrails not available on this branch");
            setHTML("scannerList", `
                <div class="pg-empty">
                    <div class="pg-empty-icon">🔒</div>
                    Guardrails available on railway-guardrails branch
                </div>
            `);
            setHTML("guardsByScanner", "");
            return;
        }

        // Totals
        const inputScans = d.input_scans || 0;
        const outputScans = d.output_scans || 0;
        const totalScans = inputScans + outputScans;
        const blocked = d.blocked_count || 0;
        const rate = totalScans > 0 ? ((blocked / totalScans) * 100).toFixed(1) : "0.0";

        setText("guardsTotal", fmt(totalScans));
        setText("guardsInput", fmt(inputScans));
        setText("guardsOutput", fmt(outputScans));
        setText("guardsBlocked", fmt(blocked));
        setText("guardsBlockRate", rate + "% block rate");

        // Blocked by scanner
        const byScanner = d.blocked_by_scanner || {};
        const scannerNames = Object.keys(byScanner);
        if (scannerNames.length > 0) {
            setHTML("guardsByScanner", scannerNames.map(name =>
                `<div class="pg-breakdown-row">
                    <span class="pg-breakdown-label">${escHtml(name)}</span>
                    <span class="pg-breakdown-value">${fmt(byScanner[name])}</span>
                </div>`
            ).join(""));
        } else {
            setHTML("guardsByScanner", "");
        }

        // Scanner status
        const scanners = d.scanners || [];
        if (scanners.length > 0) {
            setHTML("scannerList", scanners.map(s => {
                let cls = "unavailable";
                let label = "unavailable";
                if (s.status === "loaded") { cls = "loaded"; label = "loaded"; }
                else if (s.status === "lazy") { cls = "lazy"; label = "lazy"; }
                return `<div class="pg-scanner-row">
                    <span class="pg-scanner-name">${escHtml(s.name)}</span>
                    <span class="pg-scanner-badge ${cls}">${label}</span>
                </div>`;
            }).join(""));
        } else {
            setHTML("scannerList", `
                <div class="pg-empty">
                    <div class="pg-empty-icon">⚙️</div>
                    No scanners registered
                </div>
            `);
        }

        // Recent blocks
        const recent = d.recent_blocks || [];
        if (recent.length > 0) {
            setHTML("recentBlocks", recent.map(b =>
                `<div class="pg-block-item">
                    <span class="pg-block-time">${fmtTime(b.timestamp)}</span>
                    <span class="pg-block-scanner">${escHtml(b.scanner)}</span>
                    <span class="pg-block-text">${escHtml(b.text)}</span>
                </div>`
            ).join(""));
        } else {
            setHTML("recentBlocks", `
                <div class="pg-empty">
                    <div class="pg-empty-icon">🛡️</div>
                    No blocked queries yet
                </div>
            `);
        }

    } catch (e) {
        console.error("Failed to fetch guardrails:", e);
    }
}

// ── HTML Escaping ─────────────────────────────────────────
function escHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ── Refresh Loop ──────────────────────────────────────────
async function refresh() {
    await Promise.all([fetchSystem(), fetchGuardrails()]);
    lastRefresh = new Date();
    updateRefreshIndicator();
}

function updateRefreshIndicator() {
    const el = document.getElementById("refreshIndicator");
    if (!el) return;
    if (lastRefresh) {
        const t = lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        el.textContent = `Last refresh: ${t} · Next in ${REFRESH_MS / 1000}s`;
    }
}

// Countdown timer for next refresh display
setInterval(() => {
    if (!lastRefresh) return;
    const el = document.getElementById("refreshIndicator");
    if (!el) return;
    const elapsed = Date.now() - lastRefresh.getTime();
    const remaining = Math.max(0, Math.ceil((REFRESH_MS - elapsed) / 1000));
    const t = lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    el.textContent = `Last refresh: ${t} · Next in ${remaining}s`;
}, 1000);

// ── Init ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_MS);
});
