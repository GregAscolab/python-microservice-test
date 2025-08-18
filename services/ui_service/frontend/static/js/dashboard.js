/**
 * dashboard.js
 *
 * This script manages the dashboard page, which displays a map and real-time sensor data.
 * It registers handlers with the ConnectionManager to receive GPS and CAN data.
 */
function initializeDashboardPage() {
    // --- Leaflet Map Initialization ---
    var map = L.map('map').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var geoJSONLayer = L.geoJSON().addTo(map);

    // --- WebSocket Message Handlers ---

    /**
     * Handles incoming GPS data to update the map.
     * @param {object} data - GeoJSON data for the map.
     */
    const handleGpsMessage = (data) => {
        if (data) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    };

    // --- Sensor Data Table Management ---
    const pressureTableBody = document.querySelector('#pressureTable tbody');
    const angleTableBody = document.querySelector('#angleTable tbody');
    const nameCache = new Map(); // Cache for sensor values to optimize DOM updates.

    // Mappings to determine sensor type and unit from its name.
    const suffToTypeMap = new Map([
        ["_b", "pressure"],
        ["_PFAng", "angle"],
    ]);
    const typeToUnitMap = new Map([
        ["pressure", "bars"],
        ["angle", "deg"],
    ]);

    /**
     * Handles incoming CAN data to update the sensor tables.
     * @param {object} data - The sensor data message.
     */
    const handleDataMessage = (data) => {
        // If the sensor is not yet in the table, create a new row for it.
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

            // Determine which table (pressure or angle) the sensor belongs to.
            let unit = "";
            let tableBody;
            for (let [key, value] of suffToTypeMap) {
                if (data.name.includes(key)) {
                    tableBody = document.querySelector('#' + value + 'Table tbody');
                    unit = typeToUnitMap.get(value);
                    break;
                } else {
                    tableBody = angleTableBody; // Default table.
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
        // Always update the cache with the latest value.
        nameCache.set(data.name, data.value);
    };

    /**
     * Periodically updates the sensor values in the table from the cache.
     * This is more performant than updating the DOM on every single message.
     */
    const updateDisplay = () => {
        for (const [name, val] of nameCache) {
            const cell = document.getElementById(name + "_val");
            if (cell) {
                cell.textContent = val;
            }
        }
    };

    // Set up the periodic display update.
    setInterval(updateDisplay, 200);

    // --- Register handlers with ConnectionManager ---
    ConnectionManager.register('gps', handleGpsMessage);
    ConnectionManager.register('can_data', handleDataMessage);
}

// The initializeDashboardPage function will be called by app.js when the page is loaded.
