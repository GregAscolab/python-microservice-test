// --- Dashboard Page ---
(function(window) {
    let map;
    let geoJSONLayer;
    let pressureTable;
    let angleTable;
    let ws_gps;
    let ws_data;

    function initDashboardPage() {
        console.log("Initializing Dashboard page...");

        // --- Initialize UI Components ---
        const mapContainer = document.getElementById('map-dashboard');
        if (!mapContainer) return; // In case the element is not there

        map = L.map(mapContainer).setView([51.505, -0.09], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        geoJSONLayer = L.geoJSON().addTo(map);

        // --- WebSocket for GPS Data ---
        ws_gps = ConnectionManager.getSocket('/ws_gps');
        ws_gps.onmessage = function(event) {
            var data = JSON.parse(event.data);
            if (data && geoJSONLayer) {
                geoJSONLayer.clearLayers();
                geoJSONLayer.addData(data);
                map.fitBounds(geoJSONLayer.getBounds());
            }
        };

        // --- WebSocket for Sensor Data ---
        ws_data = ConnectionManager.getSocket('/ws_data');
        const nameCache = new Map();

        const suffToTypeMap = new Map([["_b", "pressure"], ["_PFAng", "angle"]]);
        const typeToUnitMap = new Map([["pressure", "bars"], ["angle", "deg"]]);

        ws_data.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const sensorName = data.name;
            const sensorValue = data.value;

            if (!nameCache.has(sensorName)) {
                nameCache.set(sensorName, sensorValue);

                let unit = "";
                let targetTable;
                for (let [key, value] of suffToTypeMap) {
                    if (sensorName.includes(key)) {
                        targetTable = (value === 'pressure') ? pressureTableBody : angleTableBody;
                        unit = typeToUnitMap.get(value);
                        break;
                    }
                }
                if (targetTable) {
                    const row = targetTable.insertRow();
                    row.id = sensorName;
                    row.innerHTML = `<td>${sensorName}</td><td>${sensorValue}</td><td>${unit}</td>`;
                }
            } else {
                nameCache.set(sensorName, sensorValue);
                const row = document.getElementById(sensorName);
                if (row) {
                    row.cells[1].textContent = sensorValue;
                }
            }
        };
    }

    function cleanupDashboardPage() {
        console.log("Cleaning up Dashboard page...");
        ConnectionManager.closeSocket('/ws_gps');
        ConnectionManager.closeSocket('/ws_data');
        if (map) {
            map.remove();
            map = null;
        }
        // Clear tables
        const pressureTableBody = document.querySelector('#pressureTable tbody');
        const angleTableBody = document.querySelector('#angleTable tbody');
        if(pressureTableBody) pressureTableBody.innerHTML = "";
        if(angleTableBody) angleTableBody.innerHTML = "";
    }

    // Expose functions to global scope
    window.initDashboardPage = initDashboardPage;
    window.cleanupDashboardPage = cleanupDashboardPage;

})(window);
