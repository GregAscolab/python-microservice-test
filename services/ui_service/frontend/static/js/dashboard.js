// --- Dashboard Page ---
(function(window) {
    let map;
    let geoJSONLayer;
    const pressureTableBody = document.querySelector('#pressureTable tbody');
    const angleTableBody = document.querySelector('#angleTable tbody');
    let ws_gps;
    let ws_data;
    const nameCache = new Map();
    const suffToTypeMap = new Map([["_b", "pressure"], ["_PFAng", "angle"]]);
    const typeToUnitMap = new Map([["pressure", "bars"], ["angle", "deg"]]);

    function updateCell(sensorName, sensorValue) {
        let id_val = sensorName + "_val"
        const cell_val = document.getElementById(id_val);
        if (cell_val) {
            cell_val.textContent = sensorValue;
        }
        else {}
    }
    function updateTables() {
        for (let [sensorName, sensorValue] of nameCache) {
            updateCell(sensorName, sensorValue);
        }
    }

    setInterval(updateTables, 150)

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

        // --- NATS Subscription for GPS Data ---
        const textDecoder = new TextDecoder();
        NatsConnectionManager.subscribe('gps', (m) => {
            const data = JSON.parse(textDecoder.decode(m.data));
            if (data && geoJSONLayer) {
                geoJSONLayer.clearLayers();
                geoJSONLayer.addData(data);
                map.fitBounds(geoJSONLayer.getBounds());
            }
        });

        // --- NATS Subscription for Sensor Data ---
        NatsConnectionManager.subscribe('can_data', (m) => {
            const data = JSON.parse(textDecoder.decode(m.data));
            const sensorName = data.name;
            const sensorValue = data.value;

            if (!nameCache.has(sensorName)) {
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
                    row.innerHTML = `<td>${sensorName}</td><td id=${sensorName}_val>${sensorValue}</td><td>${unit}</td>`;
                }
            } else {
                // updateCell(sensorName, sensorValue)
            }

            nameCache.set(sensorName, sensorValue);
        });
    }

    function cleanupDashboardPage() {
        console.log("Cleaning up Dashboard page...");
        // NATS subscriptions are managed globally by NatsConnectionManager
        if (map) {
            map.remove();
            map = null;
        }
        // Clear tables
        if(pressureTableBody) pressureTableBody.innerHTML = "";
        if(angleTableBody) angleTableBody.innerHTML = "";
    }

    // Expose functions to global scope
    window.initDashboardPage = initDashboardPage;
    window.cleanupDashboardPage = cleanupDashboardPage;

})(window);
