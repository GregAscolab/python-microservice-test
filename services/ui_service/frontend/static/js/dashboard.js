(function() {
    let map, geoJSONLayer, intervalID;
    let isInitialized = false;
    const nameCache = new Map(); // Cache to store received names/values
    const pressureTableBody = document.querySelector('#pressureTable tbody');
    const angleTableBody = document.querySelector('#angleTable tbody');

    const suffToTypeMap = new Map([
        ["_b", "pressure"],
        ["_PFAng", "angle"],
    ]);

    const typeToUnitMap = new Map([
        ["pressure", "bars"],
        ["angle", "deg"],
    ]);

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
        if (isInitialized) {
            return;
        }
        console.log("Initializing Dashboard page...");

        map = L.map('map-dashboard').setView([51.505, -0.09], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        geoJSONLayer = L.geoJSON().addTo(map);

        isInitialized = true;
        console.log("Dashboard page initialization complete.");
    }

    function onWsGpsOpen() {
        console.log("Dashboard GPS WebSocket opened.");
        initDashboardPage();
    }

    function onWsGpsMessage(event) {
        const data = JSON.parse(event.data);
        if (data && geoJSONLayer) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    }

    function onWsDataOpen() {
        console.log("Dashboard Data WebSocket opened.");
        initDashboardPage();
    }

    function onWsDataMessage(event) {
        const data = JSON.parse(event.data);
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
    }

    // --- WebSocket Connections ---
    ConnectionManager.getSocket('/ws_gps', onWsGpsOpen, onWsGpsMessage);
    ConnectionManager.getSocket('/ws_data', onWsDataOpen, onWsDataMessage);

    function cleanupDashboardPage() {
        console.log("Cleaning up Dashboard page...");
        if (intervalID) {
            clearInterval(intervalID);
        }
        ConnectionManager.closeSocket('/ws_gps');
        ConnectionManager.closeSocket('/ws_data');

        if (map) {
            map.remove();
            map = null;
        }
        // Clear tables
        if(pressureTableBody) pressureTableBody.innerHTML = "";
        if(angleTableBody) angleTableBody.innerHTML = "";

        isInitialized = false;
        nameCache.clear();
        console.log("Dashboard page cleanup complete.");
    };
})();
