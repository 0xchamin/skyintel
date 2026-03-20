/* vessels.js — BillboardCollection + viewport + toggles for vessel tracking */

const VESSEL_COLORS = {
    cargo:        Cesium.Color.fromCssColorString("#4FC3F7"),
    tanker:       Cesium.Color.fromCssColorString("#FF8A65"),
    passenger:    Cesium.Color.WHITE,
    military:     Cesium.Color.fromCssColorString("#EF5350"),
    fishing:      Cesium.Color.fromCssColorString("#66BB6A"),
    recreational: Cesium.Color.fromCssColorString("#00BCD4"),
    high_speed:   Cesium.Color.fromCssColorString("#FFD54F"),
    special:      Cesium.Color.fromCssColorString("#AB47BC"),
    unknown:      Cesium.Color.fromCssColorString("#9E9E9E"),
};

const VESSEL_HEADING_BUCKET = 10;
const VESSEL_ICON_SIZE = 24;
const VESSEL_REFRESH_INTERVAL = 10000;

let vesselBillboards = null;
let vesselLabels = null;
let vesselState = {};
let vesselToggles = {
    cargo: true, tanker: true, passenger: true, military: true,
    fishing: true, recreational: true, special: true, high_speed: true, unknown: false,
};
let vesselCounts = {};

// ── Icon cache ──────────────────────────────────────────────
const vesselIconCache = {};

function drawCargo(ctx, s) {
    const h = s / 2;
    // Boxy hull
    ctx.beginPath();
    ctx.moveTo(0, -h + 2);
    ctx.lineTo(h * 0.4, -h);
    ctx.lineTo(h * 0.4, h * 0.6);
    ctx.lineTo(h * 0.25, h);
    ctx.lineTo(-h * 0.25, h);
    ctx.lineTo(-h * 0.4, h * 0.6);
    ctx.lineTo(-h * 0.4, -h);
    ctx.closePath();
    ctx.fill();
    // Containers (small rectangles on deck)
    ctx.globalAlpha = 0.5;
    ctx.fillRect(-h * 0.25, -h * 0.5, h * 0.5, h * 0.3);
    ctx.fillRect(-h * 0.25, -h * 0.1, h * 0.5, h * 0.3);
    ctx.globalAlpha = 1.0;
}

function drawTanker(ctx, s) {
    const h = s / 2;
    // Long rounded hull
    ctx.beginPath();
    ctx.moveTo(0, -h + 1);
    ctx.quadraticCurveTo(h * 0.45, -h * 0.6, h * 0.4, 0);
    ctx.quadraticCurveTo(h * 0.35, h * 0.7, 0, h);
    ctx.quadraticCurveTo(-h * 0.35, h * 0.7, -h * 0.4, 0);
    ctx.quadraticCurveTo(-h * 0.45, -h * 0.6, 0, -h + 1);
    ctx.closePath();
    ctx.fill();
    // Dome tanks
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.arc(0, -h * 0.3, h * 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(0, h * 0.15, h * 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1.0;
}

function drawPassenger(ctx, s) {
    const h = s / 2;
    // Sleek hull
    ctx.beginPath();
    ctx.moveTo(0, -h + 1);
    ctx.lineTo(h * 0.35, -h * 0.4);
    ctx.lineTo(h * 0.35, h * 0.5);
    ctx.lineTo(h * 0.2, h);
    ctx.lineTo(-h * 0.2, h);
    ctx.lineTo(-h * 0.35, h * 0.5);
    ctx.lineTo(-h * 0.35, -h * 0.4);
    ctx.closePath();
    ctx.fill();
    // Superstructure
    ctx.globalAlpha = 0.5;
    ctx.fillRect(-h * 0.2, -h * 0.3, h * 0.4, h * 0.6);
    ctx.globalAlpha = 1.0;
}

function drawMilitary(ctx, s) {
    const h = s / 2;
    // Angular warship
    ctx.beginPath();
    ctx.moveTo(0, -h);
    ctx.lineTo(h * 0.3, -h * 0.3);
    ctx.lineTo(h * 0.35, h * 0.4);
    ctx.lineTo(h * 0.15, h);
    ctx.lineTo(-h * 0.15, h);
    ctx.lineTo(-h * 0.35, h * 0.4);
    ctx.lineTo(-h * 0.3, -h * 0.3);
    ctx.closePath();
    ctx.fill();
}

function drawFishing(ctx, s) {
    const h = s / 2;
    // Small boat
    ctx.beginPath();
    ctx.moveTo(0, -h + 2);
    ctx.lineTo(h * 0.3, -h * 0.2);
    ctx.lineTo(h * 0.3, h * 0.5);
    ctx.lineTo(h * 0.15, h);
    ctx.lineTo(-h * 0.15, h);
    ctx.lineTo(-h * 0.3, h * 0.5);
    ctx.lineTo(-h * 0.3, -h * 0.2);
    ctx.closePath();
    ctx.fill();
    // Mast
    ctx.strokeStyle = ctx.fillStyle;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, -h * 0.6);
    ctx.lineTo(0, h * 0.3);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(-h * 0.25, -h * 0.1);
    ctx.lineTo(h * 0.25, -h * 0.1);
    ctx.stroke();
}

function drawRecreational(ctx, s) {
    const h = s / 2;
    // Sailboat hull
    ctx.beginPath();
    ctx.moveTo(0, -h * 0.2);
    ctx.lineTo(h * 0.25, h * 0.4);
    ctx.lineTo(h * 0.1, h);
    ctx.lineTo(-h * 0.1, h);
    ctx.lineTo(-h * 0.25, h * 0.4);
    ctx.closePath();
    ctx.fill();
    // Sail triangle
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(0, -h);
    ctx.lineTo(h * 0.3, h * 0.1);
    ctx.lineTo(0, h * 0.1);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1.0;
}

function drawHighSpeed(ctx, s) {
    const h = s / 2;
    // Sleek narrow hull
    ctx.beginPath();
    ctx.moveTo(0, -h);
    ctx.lineTo(h * 0.25, -h * 0.2);
    ctx.lineTo(h * 0.3, h * 0.6);
    ctx.lineTo(0, h);
    ctx.lineTo(-h * 0.3, h * 0.6);
    ctx.lineTo(-h * 0.25, -h * 0.2);
    ctx.closePath();
    ctx.fill();
}

function drawSpecial(ctx, s) {
    const h = s / 2;
    // Tug shape — wide and short
    ctx.beginPath();
    ctx.moveTo(0, -h + 3);
    ctx.lineTo(h * 0.4, -h * 0.1);
    ctx.lineTo(h * 0.4, h * 0.5);
    ctx.lineTo(h * 0.2, h);
    ctx.lineTo(-h * 0.2, h);
    ctx.lineTo(-h * 0.4, h * 0.5);
    ctx.lineTo(-h * 0.4, -h * 0.1);
    ctx.closePath();
    ctx.fill();
}

function drawUnknown(ctx, s) {
    const h = s / 2;
    ctx.beginPath();
    ctx.arc(0, 0, h * 0.35, 0, Math.PI * 2);
    ctx.fill();
}

const VESSEL_DRAW_FNS = {
    cargo: drawCargo, tanker: drawTanker, passenger: drawPassenger,
    military: drawMilitary, fishing: drawFishing, recreational: drawRecreational,
    high_speed: drawHighSpeed, special: drawSpecial, unknown: drawUnknown,
};

function vesselIcon(type, color, heading) {
    const bucket = Math.round((heading || 0) / VESSEL_HEADING_BUCKET) * VESSEL_HEADING_BUCKET % 360;
    const key = `${type}-${bucket}`;
    if (vesselIconCache[key]) return vesselIconCache[key];

    const s = VESSEL_ICON_SIZE;
    const c = document.createElement("canvas");
    c.width = s; c.height = s;
    const ctx = c.getContext("2d");

    ctx.translate(s / 2, s / 2);
    ctx.rotate((bucket * Math.PI) / 180);

    ctx.fillStyle = color.toCssColorString();
    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 3;

    const drawFn = VESSEL_DRAW_FNS[type] || drawUnknown;
    drawFn(ctx, s);

    const dataUrl = c.toDataURL();
    vesselIconCache[key] = dataUrl;
    return dataUrl;
}

// ── Fetch ───────────────────────────────────────────────────
async function fetchVessels(bbox) {
    try {
        const params = bbox
            ? `?lat_min=${bbox.lat_min}&lat_max=${bbox.lat_max}&lon_min=${bbox.lon_min}&lon_max=${bbox.lon_max}`
            : "";
        const resp = await fetch(`/api/vessels${params}`);
        return await resp.json();
    } catch (e) {
        console.error("Fetch vessels failed:", e);
        return [];
    }
}

// ── Update state ────────────────────────────────────────────
function updateVesselState(vessels) {
    const now = performance.now() / 1000;
    const seen = new Set();

    for (const v of vessels) {
        if (v.latitude == null || v.longitude == null) continue;
        seen.add(v.mmsi);
        vesselState[v.mmsi] = {
            lat: v.latitude,
            lon: v.longitude,
            heading: v.heading || v.cog || 0,
            sog: v.sog || 0,
            vessel_type: v.vessel_type || "unknown",
            name: v.name || v.mmsi,
            lastSeen: now,
            raw: v,
        };
    }

    // Remove stale (not seen in last 2 refresh cycles)
    for (const mmsi of Object.keys(vesselState)) {
        if (now - vesselState[mmsi].lastSeen > 30) {
            delete vesselState[mmsi];
        }
    }
}

// ── Render ──────────────────────────────────────────────────
function renderVessels(viewer) {
    vesselBillboards.removeAll();
    vesselLabels.removeAll();

    const bbox = getViewportBbox(viewer);
    vesselCounts = {};

    for (const [mmsi, state] of Object.entries(vesselState)) {
        const vtype = state.vessel_type || "unknown";

        // Count all vessels regardless of toggle
        vesselCounts[vtype] = (vesselCounts[vtype] || 0) + 1;

        // Toggle filter
        if (!vesselToggles[vtype]) continue;

        // Viewport filter
        if (!isInBbox(state.lat, state.lon, bbox)) continue;

        const color = VESSEL_COLORS[vtype] || VESSEL_COLORS.unknown;
        const position = Cesium.Cartesian3.fromDegrees(state.lon, state.lat, 0);

        vesselBillboards.add({
            position: position,
            image: vesselIcon(vtype, color, state.heading),
            scale: 1.0,
            scaleByDistance: new Cesium.NearFarScalar(5e3, 1.4, 5e6, 0.3),
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            id: state.raw,
        });

        vesselLabels.add({
            position: position,
            text: state.name,
            font: "10px sans-serif",
            fillColor: color,
            style: Cesium.LabelStyle.FILL,
            verticalOrigin: Cesium.VerticalOrigin.TOP,
            pixelOffset: new Cesium.Cartesian2(0, 14),
            scaleByDistance: new Cesium.NearFarScalar(5e3, 1.0, 2e6, 0.0),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1e6),
        });
    }

    updateVesselStatusBar();
}

function updateVesselStatusBar() {
    const bar = document.getElementById("vesselStatusBar");
    if (!bar) return;
    const total = Object.keys(vesselState).length;
    const mil = vesselCounts["military"] || 0;
    const fish = vesselCounts["fishing"] || 0;
    bar.innerHTML =
        `<span class="sb-item">🚢 ${total.toLocaleString()}</span>` +
        `<span class="sb-item sb-mil">⚓ ${mil}</span>` +
        `<span class="sb-item" style="color:#66BB6A">🎣 ${fish}</span>`;
}

// ── Toggle ──────────────────────────────────────────────────
function setVesselToggle(type, enabled, viewer) {
    vesselToggles[type] = enabled;
    renderVessels(viewer);
}

// ── Init ────────────────────────────────────────────────────
async function startVesselTracking(viewer) {
    vesselBillboards = viewer.scene.primitives.add(new Cesium.BillboardCollection());
    vesselLabels = viewer.scene.primitives.add(new Cesium.LabelCollection());

    const bbox = getViewportBbox(viewer);
    const vessels = await fetchVessels(bbox);
    updateVesselState(vessels);
    renderVessels(viewer);

    setInterval(async () => {
        const bbox = getViewportBbox(viewer);
        const vessels = await fetchVessels(bbox);
        updateVesselState(vessels);
        renderVessels(viewer);
    }, VESSEL_REFRESH_INTERVAL);

    let moveTimeout = null;
    viewer.camera.moveEnd.addEventListener(() => {
        clearTimeout(moveTimeout);
        moveTimeout = setTimeout(() => renderVessels(viewer), 200);
    });
}
