/* satellites.js — BillboardCollection + tether lines for satellites */

const SAT_COLORS = {
    iss:       Cesium.Color.YELLOW,
    military:  Cesium.Color.RED,
    weather:   Cesium.Color.DEEPSKYBLUE,
    nav:       Cesium.Color.LIME,
    science:   Cesium.Color.ORANGE,
    starlink:  Cesium.Color.CORNFLOWERBLUE,
};

const SAT_REFRESH_INTERVAL = 15000;
const ALTITUDE_EXAGGERATION = 15;
const TETHER_ALPHA = 0.25;

let satBillboards = null;
let satLabels = null;
let tetherLines = null;
let satState = {};
let satToggles = { iss: true, military: true, weather: true, nav: true, science: true, starlink: false };
let satCounts = {};

// ── Icon ────────────────────────────────────────────────────
const satIconCache = {};

function satelliteIcon(color) {
    const key = color.toCssColorString();
    if (satIconCache[key]) return satIconCache[key];

    const s = 20;
    const c = document.createElement("canvas");
    c.width = s; c.height = s;
    const ctx = c.getContext("2d");

    // Diamond shape
    const h = s / 2;
    ctx.beginPath();
    ctx.moveTo(h, 1);
    ctx.lineTo(s - 1, h);
    ctx.lineTo(h, s - 1);
    ctx.lineTo(1, h);
    ctx.closePath();

    ctx.fillStyle = color.withAlpha(0.9).toCssColorString();
    ctx.shadowColor = color.toCssColorString();
    ctx.shadowBlur = 6;
    ctx.fill();

    const dataUrl = c.toDataURL();
    satIconCache[key] = dataUrl;
    return dataUrl;
}

// ── Fetch ───────────────────────────────────────────────────
async function fetchSatellites(category) {
    try {
        const resp = await fetch(`/api/satellites?category=${category}`);
        return await resp.json();
    } catch (e) {
        console.error(`Fetch satellites (${category}) failed:`, e);
        return [];
    }
}

async function fetchAllEnabled() {
    const enabled = Object.entries(satToggles).filter(([_, on]) => on).map(([cat]) => cat);
    const results = await Promise.all(enabled.map(cat => fetchSatellites(cat)));
    return results.flat();
}

// ── Rendering ───────────────────────────────────────────────
function renderSatellites(viewer, satellites) {
    satBillboards.removeAll();
    satLabels.removeAll();
    tetherLines.removeAll();

    // Count per category
    satCounts = {};
    for (const cat of Object.keys(SAT_COLORS)) satCounts[cat] = 0;

    for (const sat of satellites) {
        if (sat.latitude == null || sat.longitude == null) continue;
        const cat = sat.category || "science";
        satCounts[cat] = (satCounts[cat] || 0) + 1;

        const color = SAT_COLORS[cat] || SAT_COLORS.science;
        const altMetres = (sat.altitude_km || 400) * 1000 * ALTITUDE_EXAGGERATION;

        const position = Cesium.Cartesian3.fromDegrees(sat.longitude, sat.latitude, altMetres);
        const groundPos = Cesium.Cartesian3.fromDegrees(sat.longitude, sat.latitude, 0);

        satBillboards.add({
            position: position,
            image: satelliteIcon(color),
            scale: 1.0,
            scaleByDistance: new Cesium.NearFarScalar(1e5, 1.2, 5e7, 0.3),
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            id: sat,
        });

        satLabels.add({
            position: position,
            text: sat.name,
            font: "10px sans-serif",
            fillColor: color,
            style: Cesium.LabelStyle.FILL,
            verticalOrigin: Cesium.VerticalOrigin.TOP,
            pixelOffset: new Cesium.Cartesian2(0, 14),
            scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, 1e7, 0.0),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 5e6),
        });

        // Tether line
        tetherLines.add({
            positions: [position, groundPos],
            width: 1.0,
            material: new Cesium.Material({
                fabric: {
                    type: "Color",
                    uniforms: { color: color.withAlpha(TETHER_ALPHA) },
                },
            }),
        });
    }

    updateSatStatusBar();
}

function updateSatStatusBar() {
    const bar = document.getElementById("satStatusBar");
    if (!bar) return;

    let total = 0;
    let parts = [];
    for (const [cat, count] of Object.entries(satCounts)) {
        if (!satToggles[cat]) continue;
        total += count;
    }
    bar.innerHTML = `<span class="sb-item">🛰 ${total}</span>`;
}

// ── Toggle ──────────────────────────────────────────────────
function setSatToggle(category, enabled, viewer) {
    satToggles[category] = enabled;
    refreshSatellites(viewer);
}

async function refreshSatellites(viewer) {
    const sats = await fetchAllEnabled();
    renderSatellites(viewer, sats);
}

// ── Init ────────────────────────────────────────────────────
async function startSatelliteTracking(viewer) {
    satBillboards = viewer.scene.primitives.add(new Cesium.BillboardCollection());
    satLabels = viewer.scene.primitives.add(new Cesium.LabelCollection());
    tetherLines = viewer.scene.primitives.add(new Cesium.PolylineCollection());

    const sats = await fetchAllEnabled();
    renderSatellites(viewer, sats);

    setInterval(async () => {
        const sats = await fetchAllEnabled();
        renderSatellites(viewer, sats);
    }, SAT_REFRESH_INTERVAL);
}
