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
const VESSEL_ICON_SIZE = 28;
const VESSEL_REFRESH_INTERVAL = 10000;

let vesselBillboards = null;
let vesselLabels = null;
let vesselState = {};
let vesselToggles = {
    cargo: true, tanker: true, passenger: true, military: true,
    fishing: true, recreational: true, special: true, high_speed: true, unknown: false,
};
let vesselCounts = {};

// ── SVG path data for vessel icons ──────────────────────────
// All paths are designed pointing UP (0°), centered on (0,0), fitting ~24x24

const VESSEL_PATHS = {
    // Cargo: boxy container ship with bridge aft
    cargo: [
        "M 0,-11 L 4,-9 L 4.5,-3 L 4.5,6 L 3,10 L -3,10 L -4.5,6 L -4.5,-3 L -4,-9 Z",  // hull
        "M -3.5,-7 L 3.5,-7 L 3.5,-2 L -3.5,-2 Z",   // forward containers
        "M -3.5,-1 L 3.5,-1 L 3.5,4 L -3.5,4 Z",     // aft containers
        "M -2,5 L 2,5 L 2,8 L -2,8 Z",                // bridge
    ],
    // Tanker: long rounded ship with dome tanks
    tanker: [
        "M 0,-11 C 4,-9 5,-4 5,0 C 5,5 4,8 2.5,10 L -2.5,10 C -4,8 -5,5 -5,0 C -5,-4 -4,-9 0,-11 Z",
        "M 0,-6 m -2.5,0 a 2.5,2.5 0 1,0 5,0 a 2.5,2.5 0 1,0 -5,0",  // forward tank
        "M 0,1 m -2.5,0 a 2.5,2.5 0 1,0 5,0 a 2.5,2.5 0 1,0 -5,0",   // aft tank
    ],
    // Passenger: cruise ship with multi-deck superstructure
    passenger: [
        "M 0,-11 L 3.5,-8 L 4,-2 L 4,6 L 2.5,10 L -2.5,10 L -4,6 L -4,-2 L -3.5,-8 Z",
        "M -3,-7 L 3,-7 L 3,7 L -3,7 Z",       // superstructure
        "M -2,-6 L 2,-6 L 2,-4 L -2,-4 Z",     // upper deck
        "M -2,-3 L 2,-3 L 2,-1 L -2,-1 Z",     // mid deck
        "M -2,0 L 2,0 L 2,2 L -2,2 Z",         // lower deck
        "M -1,3 L 1,3 L 1,6 L -1,6 Z",         // funnel
    ],
    // Military: angular stealth warship
    military: [
        "M 0,-12 L 2,-8 L 3.5,-4 L 4,0 L 3.5,4 L 2,8 L 1,10 L -1,10 L -2,8 L -3.5,4 L -4,0 L -3.5,-4 L -2,-8 Z",
        "M -1.5,-5 L 1.5,-5 L 2,-1 L -2,-1 Z",  // forward turret
        "M -2,1 L 2,1 L 2,5 L -2,5 Z",          // bridge
        "M -1,6 L 1,6 L 0.5,8 L -0.5,8 Z",     // aft
    ],
    // Fishing: trawler with outrigger booms
    fishing: [
        "M 0,-9 L 3,-6 L 3.5,2 L 2.5,8 L -2.5,8 L -3.5,2 L -3,-6 Z",  // hull
        "M 0,-7 L 0,5",                          // mast (drawn as stroke)
        "M -7,-2 L 0,-5 L 7,-2",                 // outrigger booms
    ],
    // Recreational: sailboat with sail
    recreational: [
        "M 0,-3 L 2.5,3 L 2,8 L -2,8 L -2.5,3 Z",            // hull
        "M 0.5,-11 L 0.5,-2 L 5,-2 Z",                        // mainsail
        "M -0.5,-9 L -0.5,-2 L -3.5,-2 Z",                    // jib
        "M 0,-11 L 0,6",                                        // mast (stroke)
    ],
    // High speed: sleek catamaran / hydrofoil
    high_speed: [
        "M 0,-12 L 2,-7 L 2.5,-2 L 3,5 L 1,10 L -1,10 L -3,5 L -2.5,-2 L -2,-7 Z",
        "M 0,-10 L 1,-6 L -1,-6 Z",             // bow point
        "M -1.5,0 L 1.5,0 L 1.5,3 L -1.5,3 Z", // cabin
        "M -4,2 L -2.5,0 L -2.5,5 L -4,4 Z",   // left sponson
        "M 4,2 L 2.5,0 L 2.5,5 L 4,4 Z",       // right sponson
    ],
    // Special: tug / utility vessel
    special: [
        "M 0,-8 L 3.5,-5 L 4,0 L 4,5 L 2.5,8 L -2.5,8 L -4,5 L -4,0 L -3.5,-5 Z",
        "M -2.5,-3 L 2.5,-3 L 2.5,2 L -2.5,2 Z",  // wheelhouse
        "M -1.5,3 L 1.5,3 L 1.5,6 L -1.5,6 Z",    // aft structure
        "M -1,-5 L 1,-5 L 1,-3.5 L -1,-3.5 Z",     // fwd bollard
    ],
    // Unknown: simple diamond marker
    unknown: [
        "M 0,-6 L 4,0 L 0,6 L -4,0 Z",
    ],
};

// ── Icon rendering ──────────────────────────────────────────
const vesselIconCache = {};

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

    const colorStr = color.toCssColorString();
    const paths = VESSEL_PATHS[type] || VESSEL_PATHS.unknown;

    ctx.shadowColor = "rgba(0,0,0,0.6)";
    ctx.shadowBlur = 3;

    for (let i = 0; i < paths.length; i++) {
        const d = paths[i];

        // Detect stroke-only paths (mast lines, booms)
        const isStroke = /^M\s+[\d.\-]+,[\d.\-]+\s+L\s+[\d.\-]+,[\d.\-]+(\s+L\s+[\d.\-]+,[\d.\-]+)?$/.test(d.trim())
            && (type === "fishing" || type === "recreational");

        if (i === 0) {
            // Hull — full opacity fill + subtle stroke
            ctx.fillStyle = colorStr;
            ctx.strokeStyle = "rgba(0,0,0,0.3)";
            ctx.lineWidth = 0.5;
            const p = new Path2D(d);
            ctx.fill(p);
            ctx.shadowBlur = 0;
            ctx.stroke(p);
        } else if (isStroke) {
            // Mast / boom lines
            ctx.strokeStyle = colorStr;
            ctx.lineWidth = 1.2;
            ctx.shadowBlur = 0;
            const p = new Path2D(d);
            ctx.stroke(p);
        } else {
            // Superstructure / details — slightly darker
            ctx.fillStyle = colorStr;
            ctx.globalAlpha = 0.45;
            ctx.shadowBlur = 0;
            const p = new Path2D(d);
            ctx.fill(p);
            ctx.globalAlpha = 1.0;
        }
    }

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

    for (const v of vessels) {
        if (v.latitude == null || v.longitude == null) continue;
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
            pixelOffset: new Cesium.Cartesian2(0, 16),
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
