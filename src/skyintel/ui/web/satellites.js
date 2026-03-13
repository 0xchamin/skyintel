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

function issIcon() {
    const key = "iss-main";
    if (satIconCache[key]) return satIconCache[key];

    const s = 40;
    const c = document.createElement("canvas");
    c.width = s; c.height = s;
    const ctx = c.getContext("2d");
    const h = s / 2;

    // Solar panels (two wide rectangles)
    ctx.fillStyle = "rgba(255, 214, 0, 0.9)";
    ctx.fillRect(2, h - 3, 14, 6);   // left panel
    ctx.fillRect(s - 16, h - 3, 14, 6); // right panel

    // Central module (small bright core)
    ctx.fillStyle = "#FFD600";
    ctx.shadowColor = "#FFD600";
    ctx.shadowBlur = 8;
    ctx.fillRect(h - 4, h - 4, 8, 8);

    // Truss (connecting line)
    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(255, 214, 0, 0.7)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(2, h);
    ctx.lineTo(s - 2, h);
    ctx.stroke();

    const dataUrl = c.toDataURL();
    satIconCache[key] = dataUrl;
    return dataUrl;
}


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

        // satBillboards.add({
        //     position: position,
        //     image: satelliteIcon(color),
        //     scale: 1.0,
        //     scaleByDistance: new Cesium.NearFarScalar(1e5, 1.2, 5e7, 0.3),
        //     verticalOrigin: Cesium.VerticalOrigin.CENTER,
        //     id: sat,
            
        // });
        const isISS = sat.name && sat.name.toUpperCase().includes("ZARYA");

        satBillboards.add({
            position: position,
            image: isISS ? issIcon() : satelliteIcon(color),
            scale: isISS ? 1.4 : 1.0,
            scaleByDistance: new Cesium.NearFarScalar(1e5, isISS ? 1.8 : 1.2, 5e7, isISS ? 0.6 : 0.3),
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            id: sat,
        });

        satLabels.add({
            position: position,
            text: isISS ? "ISS" : sat.name,
            font: isISS ? "bold 13px sans-serif" : "10px sans-serif",
            fillColor: isISS ? Cesium.Color.YELLOW : color,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: isISS ? 2 : 0,
            verticalOrigin: Cesium.VerticalOrigin.TOP,
            pixelOffset: new Cesium.Cartesian2(0, isISS ? 18 : 14),
            scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, isISS ? 5e7 : 1e7, 0.0),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, isISS ? 5e7 : 5e6),
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
