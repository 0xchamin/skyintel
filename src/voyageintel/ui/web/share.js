/* share.js — snapshot serialization + Web Share API + clipboard fallback */

function getViewState() {
    const cam = viewer.camera;
    const pos = cam.positionCartographic;
    return {
        lon: Cesium.Math.toDegrees(pos.longitude),
        lat: Cesium.Math.toDegrees(pos.latitude),
        alt: pos.height,
        heading: Cesium.Math.toDegrees(cam.heading),
        pitch: Cesium.Math.toDegrees(cam.pitch),
        roll: Cesium.Math.toDegrees(cam.roll),
        flights: { ...flightToggles },
        sats: { ...satToggles },
    };
}

function restoreViewState(state) {
    viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(state.lon, state.lat, state.alt),
        orientation: {
            heading: Cesium.Math.toRadians(state.heading),
            pitch: Cesium.Math.toRadians(state.pitch),
            roll: Cesium.Math.toRadians(state.roll),
        },
        duration: 1.5,
    });

    if (state.flights) {
        for (const [type, on] of Object.entries(state.flights)) {
            flightToggles[type] = on;
        }
    }
    if (state.sats) {
        for (const [cat, on] of Object.entries(state.sats)) {
            satToggles[cat] = on;
        }
    }

    document.querySelectorAll(".chip").forEach(chip => {
        const type = chip.dataset.type;
        const value = chip.dataset.value;
        if (type === "flight" && state.flights && value in state.flights) {
            chip.classList.toggle("active", state.flights[value]);
        } else if (type === "sat" && state.sats && value in state.sats) {
            chip.classList.toggle("active", state.sats[value]);
        }
    });
}

function buildShareUrl() {
    const state = getViewState();
    const encoded = btoa(JSON.stringify(state));
    const url = new URL(window.location.href);
    url.searchParams.set("view", encoded);
    url.hash = "";
    return url.toString();
}

async function takeScreenshot() {
    try {
        viewer.render();
        const canvas = viewer.scene.canvas;
        const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
        return new File([blob], "voyageintel-snapshot.png", { type: "image/png" });
    } catch (e) {
        console.error("Screenshot failed:", e);
        return null;
    }
}

async function shareSnapshot() {
    const url = buildShareUrl();

    if (navigator.share) {
        try {
            const shareData = {
                title: "VoyageIntel",
                text: "Check out this live global view of air, space, and sea view!",
                url: url,
            };

            const screenshot = await takeScreenshot();
            if (screenshot && navigator.canShare && navigator.canShare({ files: [screenshot] })) {
                shareData.files = [screenshot];
            }

            await navigator.share(shareData);
            return;
        } catch (e) {
            if (e.name === "AbortError") return;
        }
    }

    try {
        await navigator.clipboard.writeText(url);
        showShareToast("Link copied to clipboard!");
    } catch (e) {
        prompt("Copy this link:", url);
    }
}

function showShareToast(message) {
    let toast = document.getElementById("shareToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "shareToast";
        toast.style.cssText = `
            position:fixed; top:60px; left:50%; transform:translateX(-50%);
            background:rgba(0,255,255,0.15); border:1px solid #0ff; color:#0ff;
            padding:10px 24px; border-radius:12px; font-size:13px; font-weight:600;
            z-index:999; backdrop-filter:blur(8px); transition:opacity 0.3s;
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = "1";
    setTimeout(() => { toast.style.opacity = "0"; }, 2500);
}

// Restore view from URL on page load
(function () {
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get("view");
    if (viewParam) {
        try {
            const state = JSON.parse(atob(viewParam));
            window.addEventListener("load", () => {
                setTimeout(() => restoreViewState(state), 1500);
            });
        } catch (e) {
            console.error("Invalid view state:", e);
        }
    }
})();
