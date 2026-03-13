/* layers.js — imagery layer switching + conditional terrain */

const IMAGERY_PROVIDERS = {
    dark: () => new Cesium.UrlTemplateImageryProvider({
        url: "https://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
        credit: new Cesium.Credit("© CARTO © OpenStreetMap contributors"),
    }),
    satellite: () => new Cesium.UrlTemplateImageryProvider({
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        credit: new Cesium.Credit("© Esri"),
    }),
    streets: () => new Cesium.UrlTemplateImageryProvider({
        url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        credit: new Cesium.Credit("© OpenStreetMap contributors"),
    }),
};

let _cesiumToken = null;

async function initLayers() {
    try {
        _cesiumToken = window.__CESIUM_TOKEN__ || null;
    } catch (e) {}

    const picker = document.getElementById("layerPicker");
    const terrainOpt = picker.querySelector('option[value="terrain"]');
    if (!_cesiumToken && terrainOpt) {
        terrainOpt.disabled = true;
        terrainOpt.textContent = "⛰ Terrain (needs token)";
    }

    picker.addEventListener("change", (e) => switchLayer(e.target.value));
}

function switchLayer(layer) {
    const layers = viewer.imageryLayers;
    layers.removeAll();

    if (layer === "terrain" && _cesiumToken) {
        Cesium.Ion.defaultAccessToken = _cesiumToken;
        Cesium.createWorldTerrainAsync().then(tp => { viewer.terrainProvider = tp; });
        Cesium.IonImageryProvider.fromAssetId(2).then(ip => { layers.addImageryProvider(ip); });
        return;
    }


    // Reset terrain to flat
    viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider();

    const factory = IMAGERY_PROVIDERS[layer] || IMAGERY_PROVIDERS.dark;
    layers.addImageryProvider(factory());
}

initLayers();
