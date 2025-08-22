// --- Map Page ---
(function(window) {
    let map;
    let osmLayer;
    let satelliteLayer;
    let geoJsonLayer;
    let markers = [];
    let userInteractedWithMap = false;
    let intervalId;

    function initMapPage() {
        console.log("Initializing Map page...");
        const mapContainer = document.getElementById('map-main');
        if (!mapContainer) return;

        map = L.map(mapContainer);

        osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        });

        const initialGeoJsonData = { "type": "FeatureCollection", "features": [] }; // Start with empty data
        addGeoJsonToMap(initialGeoJsonData);

        // Setup event listeners
        document.getElementById('toggleHardness-map').addEventListener('change', onToggleHardness);
        document.getElementById('mapType-map').addEventListener('change', onMapTypeChange);
        document.getElementById('resetMapView-map').addEventListener('click', onResetMapView);
        map.on('moveend zoomend', onMapInteraction);

        // Start dynamic data simulation
        intervalId = setInterval(addRandomPointToGeoJson, 5000);
    }

    function cleanupMapPage() {
        console.log("Cleaning up Map page...");
        if (intervalId) clearInterval(intervalId);
        if (map) {
            map.remove();
            map = null;
        }
    }

    // --- Event Handlers ---
    function onToggleHardness(e) {
        // This function's logic would need to be here
    }
    function onMapTypeChange(e) {
        if (!map) return;
        var mapType = e.target.value;
        if (mapType === 'plan') {
            map.removeLayer(satelliteLayer);
            osmLayer.addTo(map);
        } else {
            map.removeLayer(osmLayer);
            satelliteLayer.addTo(map);
        }
    }
    function onResetMapView() {
        fitMapToMarkers();
        userInteractedWithMap = false;
    }
    function onMapInteraction() {
        userInteractedWithMap = true;
    }

    // --- Core Functions ---
    function addGeoJsonToMap(geojsonData) {
        if (!map) return;
        if (geoJsonLayer) {
            map.removeLayer(geoJsonLayer);
        }
        geoJsonLayer = L.geoJSON(geojsonData, {
            pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
                radius: 8, fillColor: getColor(feature.properties.hardness.value),
                color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8
            }),
            onEachFeature: (feature, layer) => layer.bindPopup(`<b>Dureté:</b> ${feature.properties.hardness.value} ${feature.properties.hardness.unit}`)
        }).addTo(map);

        markers = [];
        geojsonData.features.forEach(feature => {
            markers.push({
                position: L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]),
                hardness: feature.properties.hardness.value,
                altitude: feature.properties.altitude
            });
        });

        if (!userInteractedWithMap) {
            fitMapToMarkers();
        }
        refreshPlotlyPlot();
    }

    function fitMapToMarkers() {
        if (!map || markers.length === 0) return;
        var bounds = L.latLngBounds(markers.map(m => m.position));
        map.fitBounds(bounds.pad(0.5));
    }

    function refreshPlotlyPlot() {
        // Plotly logic would go here
    }

    function addRandomPointToGeoJson() {
        // This function would need to be updated to fetch real data
    }

    function getColor(value) {
        var maxHardness = 300;
        var intensity = value / maxHardness;
        var red = Math.floor(intensity * 255);
        var green = Math.floor(255 * (1 - intensity));
        return `rgb(${red}, ${green}, 0)`;
    }

    // Expose functions to global scope
    window.initMapPage = initMapPage;
    window.cleanupMapPage = cleanupMapPage;

})(window);
