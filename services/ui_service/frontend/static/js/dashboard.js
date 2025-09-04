import ConnectionManager from './connection_manager.js';

let map;
let geoJSONLayer;
const pressureTableBody = document.querySelector('#pressureTable tbody');
const angleTableBody = document.querySelector('#angleTable tbody');
let gpsSub;
let dataSub;
const nameCache = new Map();
const suffToTypeMap = new Map([["_b", "pressure"], ["_PFAng", "angle"], ["_Euler", "angle"], ["_Quat", "angle"]]);
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

    // --- NATS for GPS Data ---
    let lastLat = null;
    let lastLon = null;

    function updateMap() {
        if (lastLat !== null && lastLon !== null && geoJSONLayer && map) {
            const geoJsonPoint = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lastLon, lastLat]
                }
            };
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(geoJsonPoint);
            map.setView([lastLat, lastLon], map.getZoom()); // More stable than fitBounds
        }
    }

    ConnectionManager.subscribe('gps.data.>', (m) => {
        const subject = m.subject;
        const data = ConnectionManager.jsonCodec.decode(m.data);
        const value = data.value;

        if (subject.endsWith('.coordinates.1')) { // Latitude
            lastLat = value;
        } else if (subject.endsWith('.coordinates.0')) { // Longitude
            lastLon = value;
        }
        updateMap(); // Attempt to update map on each new piece of data
    }).then(sub => {
        gpsSub = sub;
    });

    // --- NATS for Sensor Data ---
    ConnectionManager.subscribe('can.data.*', (m) => {
        const subjectParts = m.subject.split('.');
        const sensorName = subjectParts[subjectParts.length - 1]; // Get the last part of the subject
        const data = ConnectionManager.jsonCodec.decode(m.data);
        const sensorValue = data.value;

        if (!nameCache.has(sensorName)) {
            let unit = "";
            let targetTable;
            for (let [key, value] of suffToTypeMap) {
                if (sensorName.includes(key)) {
                    targetTable = (value === 'pressure') ? pressureTableBody : angleTableBody;
                    unit = typeToUnitMap.get(value) || data.unit || "";
                    break;
                }
            }
            if (targetTable) {
                const row = targetTable.insertRow();
                row.id = sensorName;
                row.innerHTML = `<td>${sensorName}</td><td id="${sensorName}_val">${sensorValue}</td><td>${unit}</td>`;
            }
        }
        nameCache.set(sensorName, sensorValue);
    }).then(sub => {
        dataSub = sub;
    });
}

function cleanupDashboardPage() {
    console.log("Cleaning up Dashboard page...");
    if (gpsSub) {
        gpsSub.unsubscribe();
        gpsSub = null;
    }
    if (dataSub) {
        dataSub.unsubscribe();
        dataSub = null;
    }
    if (map) {
        map.remove();
        map = null;
    }
    // Clear tables
    if(pressureTableBody) pressureTableBody.innerHTML = "";
    if(angleTableBody) angleTableBody.innerHTML = "";

    // Clear cache
    nameCache.clear();
}

// Expose functions to global scope
window.initDashboardPage = initDashboardPage;
window.cleanupDashboardPage = cleanupDashboardPage;
