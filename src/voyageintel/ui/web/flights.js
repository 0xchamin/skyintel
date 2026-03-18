/* flights.js — BillboardCollection + viewport + toggles */

const FLIGHT_COLORS = {
    military:   Cesium.Color.RED,
    commercial: Cesium.Color.WHITE,
    private:    Cesium.Color.fromCssColorString("#CE93D8"),
};

const HEADING_BUCKET = 10;
const ICON_SIZE = 36;
const REFRESH_INTERVAL = 10000;
const STALE_SECONDS = 120;
const DEG_TO_RAD = Math.PI / 180;
const EARTH_RADIUS = 6371000;

let billboards = null;
let labels = null;
let flightCount = 0;
let militaryCount = 0;
let privateCount = 0;

let aircraftState = {};
let flightToggles = { commercial: true, military: true, private: true };

// ── Icon cache ──────────────────────────────────────────────
const iconCache = {};

function airplaneIcon(color, heading) {
    const bucket = Math.round((heading || 0) / HEADING_BUCKET) * HEADING_BUCKET % 360;
    const key = `${color.toCssColorString()}-${bucket}`;
    if (iconCache[key]) return iconCache[key];

    const s = ICON_SIZE, h = s / 2;
    const c = document.createElement("canvas");
    c.width = s; c.height = s;
    const ctx = c.getContext("2d");

    ctx.translate(h, h);
    ctx.rotate((bucket * Math.PI) / 180);

    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(3, -7);
    ctx.lineTo(14, 0);
    ctx.lineTo(14, 2);
    ctx.lineTo(3, -1);
    ctx.lineTo(2, 8);
    ctx.lineTo(7, 12);
    ctx.lineTo(7, 14);
    ctx.lineTo(0, 11);
    ctx.lineTo(-7, 14);
    ctx.lineTo(-7, 12);
    ctx.lineTo(-2, 8);
    ctx.lineTo(-3, -1);
    ctx.lineTo(-14, 2);
    ctx.lineTo(-14, 0);
    ctx.lineTo(-3, -7);
    ctx.closePath();

    ctx.fillStyle = color.toCssColorString();
    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 3;
    ctx.fill();

    const dataUrl = c.toDataURL();
    iconCache[key] = dataUrl;
    return dataUrl;
}

// ── Viewport bbox ───────────────────────────────────────────
function getViewportBbox(viewer) {
    const rect = viewer.camera.computeViewRectangle();
    if (!rect) return null;
    return {
        lat_min: Cesium.Math.toDegrees(rect.south),
        lat_max: Cesium.Math.toDegrees(rect.north),
        lon_min: Cesium.Math.toDegrees(rect.west),
        lon_max: Cesium.Math.toDegrees(rect.east),
    };
}

function isInBbox(lat, lon, bbox) {
    if (!bbox) return true;
    if (bbox.lon_min <= bbox.lon_max) {
        return lat >= bbox.lat_min && lat <= bbox.lat_max &&
               lon >= bbox.lon_min && lon <= bbox.lon_max;
    }
    return lat >= bbox.lat_min && lat <= bbox.lat_max &&
           (lon >= bbox.lon_min || lon <= bbox.lon_max);
}

// ── Dead-reckoning ──────────────────────────────────────────
function extrapolate(state, dtSeconds) {
    if (!state.velocity_ms || !state.heading) return { lon: state.lon, lat: state.lat, alt: state.alt };

    const speed = state.velocity_ms;
    const hdgRad = state.heading * DEG_TO_RAD;
    const dist = speed * dtSeconds;

    const latRad = state.lat * DEG_TO_RAD;
    const dLat = (dist * Math.cos(hdgRad)) / EARTH_RADIUS;
    const dLon = (dist * Math.sin(hdgRad)) / (EARTH_RADIUS * Math.cos(latRad));

    const newLat = state.lat + dLat * (180 / Math.PI);
    const newLon = state.lon + dLon * (180 / Math.PI);

    const vr = state.vertical_rate || 0;
    const newAlt = Math.max(0, (state.alt || 10000) + vr * dtSeconds);

    return { lon: newLon, lat: newLat, alt: newAlt };
}

// ── Fetch ───────────────────────────────────────────────────
async function fetchFlights() {
    try {
        const resp = await fetch("/api/flights");
        return await resp.json();
    } catch (e) {
        console.error("Fetch flights failed:", e);
        return [];
    }
}

// ── Update global state ─────────────────────────────────────
function updateState(flights) {
    const now = performance.now() / 1000;

    for (const f of flights) {
        if (f.latitude == null || f.longitude == null) continue;

        aircraftState[f.icao24] = {
            lon: f.longitude,
            lat: f.latitude,
            alt: f.altitude_m || 10000,
            heading: f.heading,
            velocity_ms: f.velocity_ms,
            vertical_rate: f.vertical_rate,
            aircraft_type: f.aircraft_type,
            callsign: f.callsign || f.icao24,
            lastSeen: now,
            billboard_idx: null,
            label_idx: null,
            raw: f,

        };
    }

    for (const id of Object.keys(aircraftState)) {
        if (now - aircraftState[id].lastSeen > STALE_SECONDS) {
            delete aircraftState[id];
        }
    }
}

// ── Render (viewport + toggle filtered) ─────────────────────
function renderScene(viewer) {
    billboards.removeAll();
    labels.removeAll();

    const bbox = getViewportBbox(viewer);
    flightCount = 0;
    militaryCount = 0;
    privateCount = 0;

    let idx = 0;
    for (const [icao24, state] of Object.entries(aircraftState)) {
        // Toggle filter
        if (!flightToggles[state.aircraft_type]) continue;
        // Viewport filter
        if (!isInBbox(state.lat, state.lon, bbox)) continue;

        flightCount++;
        if (state.aircraft_type === "military") militaryCount++;
        if (state.aircraft_type === "private") privateCount++;

        const color = FLIGHT_COLORS[state.aircraft_type] || FLIGHT_COLORS.commercial;
        const position = Cesium.Cartesian3.fromDegrees(state.lon, state.lat, state.alt);

        billboards.add({
            position: position,
            image: airplaneIcon(color, state.heading),
            scale: 1.0,
            scaleByDistance: new Cesium.NearFarScalar(5e3, 1.4, 1e7, 0.2),
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            //id: icao24,
            id: state.raw,

            //id: { icao24, ...state },

        });

        labels.add({
            position: position,
            text: state.callsign,
            font: "11px sans-serif",
            fillColor: color,
            style: Cesium.LabelStyle.FILL,
            verticalOrigin: Cesium.VerticalOrigin.TOP,
            pixelOffset: new Cesium.Cartesian2(0, 18),
            scaleByDistance: new Cesium.NearFarScalar(5e3, 1.0, 3e6, 0.0),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 2e6),
        });

        state.billboard_idx = idx;
        state.label_idx = idx;
        idx++;
    }

    updateFlightStatusBar();
}

// ── Per-frame interpolation ─────────────────────────────────
function onPreRender(viewer) {
    if (!billboards || billboards.length === 0) return;
    const now = performance.now() / 1000;

    for (const state of Object.values(aircraftState)) {
        if (state.billboard_idx == null) continue;
        const dt = now - state.lastSeen;
        if (dt <= 0 || dt > 60) continue;

        const pos = extrapolate(state, dt);
        const cartesian = Cesium.Cartesian3.fromDegrees(pos.lon, pos.lat, pos.alt);

        const bb = billboards.get(state.billboard_idx);
        const lb = labels.get(state.label_idx);
        if (bb) bb.position = cartesian;
        if (lb) lb.position = cartesian;
    }
}

function updateFlightStatusBar() {
    const bar = document.getElementById("flightStatusBar");
    if (!bar) return;
    const total = Object.keys(aircraftState).length;
    const totalMil = Object.values(aircraftState).filter(s => s.aircraft_type === "military").length;
    const totalPrv = Object.values(aircraftState).filter(s => s.aircraft_type === "private").length;
    const totalComm = total - totalMil - totalPrv;
    bar.innerHTML =
        `<span class="sb-item">✈ ${totalComm}</span>` +
        `<span class="sb-item sb-mil">⚔ ${totalMil}</span>` +
        `<span class="sb-item sb-prv">🛩 ${totalPrv}</span>`;
}

// ── Toggle ──────────────────────────────────────────────────
function setFlightToggle(type, enabled, viewer) {
    flightToggles[type] = enabled;
    renderScene(viewer);
}

// ── Init ────────────────────────────────────────────────────
async function startFlightTracking(viewer) {
    billboards = viewer.scene.primitives.add(new Cesium.BillboardCollection());
    labels = viewer.scene.primitives.add(new Cesium.LabelCollection());

    viewer.scene.preRender.addEventListener(() => onPreRender(viewer));

    const flights = await fetchFlights();
    updateState(flights);
    renderScene(viewer);

    setInterval(async () => {
        const flights = await fetchFlights();
        updateState(flights);
        renderScene(viewer);
    }, REFRESH_INTERVAL);

    let moveTimeout = null;
    viewer.camera.moveEnd.addEventListener(() => {
        clearTimeout(moveTimeout);
        moveTimeout = setTimeout(() => renderScene(viewer), 200);
    });
}
