function initializeDashboardPage() {
    // --- Leaflet Map Initialization ---
    var map = L.map('map').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var geoJSONLayer = L.geoJSON().addTo(map);

    // --- WebSocket Message Handlers ---
    const handleGpsMessage = (data) => {
        // console.log("ws_gps onmessage =" + JSON.stringify(data));
        if (data) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    };

    const pressureTableBody = document.querySelector('#pressureTable tbody');
    const angleTableBody = document.querySelector('#angleTable tbody');
    const nameCache = new Map();
    const suffToTypeMap = new Map([
        ["_b", "pressure"],
        ["_PFAng", "angle"],
    ]);
    const typeToUnitMap = new Map([
        ["pressure", "bars"],
        ["angle", "deg"],
    ]);

    const handleDataMessage = (data) => {
        if (!nameCache.has(data.name)) {
            const newRow = document.createElement('tr');
            newRow.id = data.name;

            const nameCell = document.createElement('td');
            nameCell.textContent = data.name;
            newRow.appendChild(nameCell);

            const valueCell = document.createElement('td');
            valueCell.textContent = data.value;
            valueCell.id = data.name + "_val";
            valueCell.style.textAlign = "right";
            newRow.appendChild(valueCell);

            let unit = "";
            let tableBody;
            for (let [key, value] of suffToTypeMap) {
                if (data.name.includes(key)) {
                    tableBody = document.querySelector('#' + value + 'Table tbody');
                    unit = typeToUnitMap.get(value);
                    break;
                } else {
                    tableBody = angleTableBody;
                    unit = "";
                }
            }
            const unitCell = document.createElement('td');
            unitCell.textContent = unit;
            unitCell.id = data.name + "_unit";
            newRow.appendChild(unitCell);

            if (tableBody) {
                tableBody.appendChild(newRow);
            }
        }
        nameCache.set(data.name, data.value);
    };

    const updateDisplay = () => {
        for (const [name, val] of nameCache) {
            const cell = document.getElementById(name + "_val");
            if (cell) {
                cell.textContent = val;
            }
        }
    };

    setInterval(updateDisplay, 200);

    // --- Register handlers with ConnectionManager ---
    ConnectionManager.register('gps', handleGpsMessage);
    ConnectionManager.register('can_data', handleDataMessage);
}

if (typeof initializeDashboardPage === 'function') {
    initializeDashboardPage();
}
