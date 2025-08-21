(function() {
    // --- UI Elements ---
    const mapContainer = document.getElementById('map-dashboard');
    const pressureTableBody = document.querySelector('#pressureTable tbody');
    const angleTableBody = document.querySelector('#angleTable tbody');

    // --- Initialize UI Components ---
    var map = L.map(mapContainer).setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var geoJSONLayer = L.geoJSON().addTo(map);

    // --- WebSocket for GPS Data ---
    const ws_gps = ConnectionManager.getSocket('/ws_gps');
    ws_gps.onmessage = function(event) {
        var data = JSON.parse(event.data);
        if (data) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    };

    // --- WebSocket for Sensor Data ---
    const ws_data = ConnectionManager.getSocket('/ws_data');
    const nameCache = new Map(); // Cache to store received names/values

    const suffToTypeMap = new Map([
        ["_b", "pressure"],
        ["_PFAng", "angle"],
    ]);

    const typeToUnitMap = new Map([
        ["pressure", "bars"],
        ["angle", "deg"],
    ]);

    ws_data.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const sensorName = data.name;
        const sensorValue = data.value;

        // Check if the row already exists
        let row = document.getElementById(sensorName);

        if (row) {
            // Update existing row's value cell
            row.cells[1].textContent = sensorValue;
        } else {
            // Create a new row
            let unit = "";
            let targetTableBody;
            for (let [key, value] of suffToTypeMap) {
                if (sensorName.includes(key)) {
                    targetTableBody = (value === 'pressure') ? pressureTableBody : angleTableBody;
                    unit = typeToUnitMap.get(value);
                    break;
                }
            }

            if (targetTableBody) {
                row = targetTableBody.insertRow();
                row.id = sensorName;

                const cell1 = row.insertCell(0);
                const cell2 = row.insertCell(1);
                const cell3 = row.insertCell(2);

                cell1.textContent = sensorName;
                cell2.textContent = sensorValue;
                cell3.textContent = unit;
            }
        }
    };

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Dashboard page...");
        // Close WebSocket connections
        ConnectionManager.closeSocket('/ws_gps');
        ConnectionManager.closeSocket('/ws_data');

        // Clean up Leaflet map
        if (map) map.remove();
        console.log("Dashboard page cleanup complete.");
    };

})();
