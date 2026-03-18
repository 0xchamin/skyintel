/* detail.js — click-to-inspect panel + fly-to + weather */

let _viewer = null;
let _previousCamera = null;


function initDetailPanel(viewer) {
    _viewer = viewer;
    const panel = document.getElementById("detailPanel");
    const closeBtn = document.getElementById("detailClose");
    const content = document.getElementById("detailContent");

    closeBtn.addEventListener("click", () => {
        panel.classList.remove("open");
    });

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

    handler.setInputAction((click) => {
        const picked = viewer.scene.pick(click.position);
        if (!picked || !picked.primitive || !picked.primitive.id) {
            panel.classList.remove("open");
            return;
        }

        const data = picked.primitive.id;

        if (data.icao24) {
            showFlightDetail(data, content);
        } else if (data.norad_id !== undefined) {
            showSatelliteDetail(data, content);
        } else {
            panel.classList.remove("open");
            return;
        }

        panel.classList.add("open");
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function row(label, value, unit) {
    if (value == null || value === "") return "";
    const display = unit ? `${value} ${unit}` : value;
    return `<div class="detail-row">
        <span class="detail-label">${label}</span>
        <span class="detail-value">${display}</span>
    </div>`;
}

function showFlightDetail(f, el) {
    const typeColor = {
        military: "#ef5350",
        commercial: "#fff",
        private: "#CE93D8",
    };
    const color = typeColor[f.aircraft_type] || "#fff";
    const badge = `<span class="detail-badge" style="background:${color};color:#000">${(f.aircraft_type || "").toUpperCase()}</span>`;

    const altFt = f.altitude_m != null ? Math.round(f.altitude_m * 3.28084).toLocaleString() : null;
    const speedKt = f.velocity_ms != null ? Math.round(f.velocity_ms * 1.94384) : null;
    const vrFpm = f.vertical_rate != null ? Math.round(f.vertical_rate * 196.85) : null;

    const canFlyTo = f.latitude != null && f.longitude != null;

    el.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">✈ ${f.callsign || f.icao24}</div>
            ${badge}
        </div>
        ${canFlyTo ? `<button class="flyto-btn" onclick="flyToTarget(${f.latitude}, ${f.longitude}, ${f.altitude_m || 10000})">📍 Fly to aircraft</button>` : ""}
        <div class="detail-section">
            ${row("ICAO24", f.icao24)}
            ${row("Callsign", f.callsign)}
            ${row("Model", f.model)}
            ${row("Operator", f.operator)}
            ${row("Registration", f.registration)}
        </div>
        <div class="detail-section">
            ${row("Altitude", altFt, "ft")}
            ${row("Speed", speedKt, "kt")}
            ${row("Heading", f.heading != null ? Math.round(f.heading) + "°" : null)}
            ${row("Vertical Rate", vrFpm, "ft/min")}
            ${row("Squawk", f.squawk)}
        </div>
        <div class="detail-section">
            ${row("Origin", f.origin)}
            ${row("Destination", f.destination)}
            ${row("Source", f.source)}
        </div>
        <div id="aircraftMetaSection"></div>
        <div id="routeSection"></div>
        <div id="weatherSection"></div>
    `;

    // Fetch weather for aircraft location
    if (canFlyTo) {
        fetchWeather(f.latitude, f.longitude);
    }
    fetchAircraftMeta(f.icao24);
    if (f.callsign) fetchRoute(f.callsign);

}

function showSatelliteDetail(s, el) {
    if (s.name && s.name.toUpperCase().includes("ZARYA")) {
        return showISSDetail(s, el);
    }
    const catColors = {
        iss: "#FFD600", military: "#ef5350", weather: "#00BFFF",
        nav: "#00E676", science: "#FF9800", starlink: "#6495ED",
    };
    const color = catColors[s.category] || "#fff";
    const badge = `<span class="detail-badge" style="background:${color};color:#000">${(s.category || "").toUpperCase()}</span>`;

    const canFlyTo = s.latitude != null && s.longitude != null;

    el.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">🛰 ${s.name}</div>
            ${badge}
        </div>
        ${canFlyTo ? `<button class="flyto-btn" onclick="flyToTarget(${s.latitude}, ${s.longitude}, ${(s.altitude_km || 400) * 1000})">📍 Fly to satellite</button>` : ""}
        <div class="detail-section">
            ${row("NORAD ID", s.norad_id)}
            ${row("Category", s.category)}
            ${row("Altitude", s.altitude_km != null ? Math.round(s.altitude_km).toLocaleString() : null, "km")}
            ${row("Speed", s.speed_ms != null ? Math.round(s.speed_ms).toLocaleString() : null, "m/s")}
            ${row("Inclination", s.inclination, "°")}
            ${row("Latitude", s.latitude != null ? s.latitude.toFixed(4) : null)}
            ${row("Longitude", s.longitude != null ? s.longitude.toFixed(4) : null)}
        </div>
    `;
}

async function trackISS() {
    try {
        const resp = await fetch("/api/iss");
        if (!resp.ok) throw new Error("Failed to fetch ISS position");
        const data = await resp.json();
        const pos = data.position;
        if (pos.latitude == null || pos.longitude == null) return;

        // Save current camera
        _previousCamera = {
            position: _viewer.camera.position.clone(),
            heading: _viewer.camera.heading,
            pitch: _viewer.camera.pitch,
            roll: _viewer.camera.roll,
        };

        // Rotate globe to ISS location at high altitude (global view)
        _viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(pos.longitude, pos.latitude, 8000000),
            orientation: {
                heading: Cesium.Math.toRadians(0),
                pitch: Cesium.Math.toRadians(-90),
                roll: 0,
            },
            duration: 2.0,
            complete: () => {
                const backBtn = document.getElementById("backBtn");
                if (backBtn) backBtn.style.display = "block";
            },
        });

        // Open detail panel with ISS info
        const content = document.getElementById("detailContent");
        const panel = document.getElementById("detailPanel");
        showISSDetail(pos, content);
        panel.classList.add("open");
    } catch (e) {
        console.error("Track ISS failed:", e);
    }
}



// ── Fly-to ──────────────────────────────────────────────────
function flyToTarget(lat, lon, altMetres) {
    if (!_viewer) return;

    // Save current camera
    _previousCamera = {
        position: _viewer.camera.position.clone(),
        heading: _viewer.camera.heading,
        pitch: _viewer.camera.pitch,
        roll: _viewer.camera.roll,
    };

    const offset = Math.min(altMetres * 3, 500000);

    _viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, altMetres + offset),
        orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0,
        },
        duration: 2.0,
        complete: () => {
            const backBtn = document.getElementById("backBtn");
            if (backBtn) backBtn.style.display = "block";
        },
    });
}

function flyBack() {
    if (!_viewer || !_previousCamera) return;
    _viewer.camera.flyTo({
        destination: _previousCamera.position,
        orientation: {
            heading: _previousCamera.heading,
            pitch: _previousCamera.pitch,
            roll: _previousCamera.roll,
        },
        duration: 1.5,
        complete: () => {
            const backBtn = document.getElementById("backBtn");
            if (backBtn) backBtn.style.display = "none";
            _previousCamera = null;
        },
    });
}


// ── Weather ─────────────────────────────────────────────────
async function fetchWeather(lat, lon) {
    const section = document.getElementById("weatherSection");
    if (!section) return;

    section.innerHTML = `<div class="detail-section" style="opacity:0.5">Loading weather…</div>`;

    try {
        const resp = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
        if (!resp.ok) throw new Error("Failed");
        const w = await resp.json();

        const windDir = w.wind_direction != null ? degreesToCompass(w.wind_direction) : null;

        section.innerHTML = `
            <div class="detail-section">
                <div class="detail-row" style="margin-bottom:6px">
                    <span class="detail-label" style="font-size:14px;color:#0ff">☁ Weather at location</span>
                </div>
                ${row("Condition", w.description)}
                ${row("Temperature", w.temperature_c, "°C")}
                ${row("Feels like", w.feels_like_c, "°C")}
                ${row("Humidity", w.humidity_pct, "%")}
                ${row("Wind", w.wind_speed_kt != null ? `${Math.round(w.wind_speed_kt)} kt ${windDir || ""}` : null)}
                ${row("Gusts", w.wind_gusts_kt, "kt")}
                ${row("Cloud cover", w.cloud_cover_pct, "%")}
                
                ${row("Precipitation", w.precipitation_mm, "mm")}
            </div>
        `;
    } catch (e) {
        section.innerHTML = `<div class="detail-section" style="opacity:0.4">Weather unavailable</div>`;
    }
}

async function fetchAircraftMeta(icao24) {
    const section = document.getElementById("aircraftMetaSection");
    if (!section) return;
    section.innerHTML = `<div class="detail-section" style="opacity:0.5">Loading aircraft info…</div>`;
    try {
        const resp = await fetch(`/api/aircraft/${icao24}`);
        if (!resp.ok) throw new Error("Not found");
        const a = await resp.json();
        section.innerHTML = `
            <div class="detail-section">
                <div class="detail-row" style="margin-bottom:6px">
                    <span class="detail-label" style="font-size:14px;color:#0ff">🛩 Aircraft Info</span>
                </div>
                ${row("Manufacturer", a.manufacturer)}
                ${row("Type", a.type_name)}
                ${row("Type Code", a.type_code)}
                ${row("Owner", a.owner)}
                ${row("Registration", a.registration)}
            </div>
        `;
    } catch (e) {
        section.innerHTML = "";
    }
}

async function fetchRoute(callsign) {
    const section = document.getElementById("routeSection");
    if (!section) return;
    section.innerHTML = `<div class="detail-section" style="opacity:0.5">Loading route…</div>`;
    try {
        const resp = await fetch(`/api/route/${callsign}`);
        if (!resp.ok) throw new Error("Not found");
        const r = await resp.json();
        section.innerHTML = `
            <div class="detail-section">
                <div class="detail-row" style="margin-bottom:6px">
                    <span class="detail-label" style="font-size:14px;color:#0ff">🗺 Route</span>
                </div>
                ${row("Origin", r.origin_icao)}
                ${row("Destination", r.destination_icao)}
            </div>
        `;
    } catch (e) {
        section.innerHTML = "";
    }
}


function degreesToCompass(deg) {
    const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    return dirs[Math.round(deg / 22.5) % 16];
}


async function showISSDetail(s, el) {
    const badge = `<span class="detail-badge" style="background:#FFD600;color:#000">ISS</span>`;
    const canFlyTo = s.latitude != null && s.longitude != null;

    el.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">🛰 International Space Station</div>
            ${badge}
        </div>
        ${canFlyTo ? `<button class="flyto-btn" onclick="flyToTarget(${s.latitude}, ${s.longitude}, ${(s.altitude_km || 400) * 1000})">📍 Fly to ISS</button>` : ""}
        <div class="detail-section">
            ${row("Altitude", s.altitude_km != null ? Math.round(s.altitude_km).toLocaleString() : null, "km")}
            ${row("Speed", s.speed_ms != null ? Math.round(s.speed_ms).toLocaleString() : null, "m/s")}
            ${row("Latitude", s.latitude != null ? s.latitude.toFixed(4) : null)}
            ${row("Longitude", s.longitude != null ? s.longitude.toFixed(4) : null)}
        </div>
        <div id="issCrewSection"><div class="detail-section" style="opacity:0.5">Loading crew…</div></div>
        <div id="issPassesSection"></div>
        <div class="detail-section">
            <div class="detail-row" style="margin-bottom:6px">
                <span class="detail-label" style="font-size:14px;color:#0ff">📺 Live Feeds</span>
            </div>
            <a href="https://www.nasa.gov/nasalive" target="_blank" style="color:#0ff; font-size:13px; text-decoration:none;">🔴 NASA Live Stream →</a><br>
            <a href="https://eol.jsc.nasa.gov/ESRS/HDEV/" target="_blank" style="color:#0ff; font-size:13px; text-decoration:none; margin-top:4px; display:inline-block;">🌍 Earth HD Camera →</a>
        </div>
    `;

    // Fetch crew
    try {
        const resp = await fetch("/api/iss");
        if (resp.ok) {
            const data = await resp.json();
            const crew = data.crew?.crew || [];
            const section = document.getElementById("issCrewSection");
            if (section && crew.length > 0) {
                section.innerHTML = `
                    <div class="detail-section">
                        <div class="detail-row" style="margin-bottom:6px">
                            <span class="detail-label" style="font-size:14px;color:#0ff">👥 Crew (${crew.length})</span>
                        </div>
                        ${crew.map(c => `<div class="detail-row"><span class="detail-value">• ${c.name}</span></div>`).join("")}
                    </div>
                `;
            }
        }
    } catch (e) {}

    // Fetch next passes (use ISS position as observer for demo, ideally user location)
    if (canFlyTo) {
        fetchWeather(s.latitude, s.longitude);
    }
}
