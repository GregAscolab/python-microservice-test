import ConnectionManager from './connection_manager.js';

let map;
let marker;
let skyviewDiv;
let gpsSub;

function initGpsPage() {
    console.log("Initializing GPS page...");

    // --- UI Elements ---
    const mapContainer = document.getElementById('map-gps');
    skyviewDiv = document.getElementById('skyviewChart');
    const gpsTableBody = document.querySelector('#gpsDataTable tbody');

    if (!mapContainer || !skyviewDiv || !gpsTableBody) return;

    // --- Leaflet Map Initialization ---
    map = L.map(mapContainer).setView([45.525, 4.924], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    marker = L.marker([45.525, 4.924]).addTo(map);

    // --- Plotly Skyview Initialization ---
    const layout = {
        polar: {
            radialaxis: { tickfont: { size: 8 }, angle: 90, tickangle: 90, range: [90, 0] },
            angularaxis: { tickfont: { size: 10 }, rotation: 90, direction: "clockwise" }
        },
        showlegend: false,
        margin: { l: 40, r: 40, t: 40, b: 40 }
    };
    Plotly.newPlot(skyviewDiv, [], layout);

    let gpsState = {}; // Local cache for the entire GPS data structure

    // Helper to set a value in a nested object based on a path array
    function setNestedValue(obj, path, value) {
        let schema = obj;
        for (let i = 0; i < path.length - 1; i++) {
            const key = path[i];
            if (!schema[key]) {
                schema[key] = (typeof path[i+1] === 'number') ? [] : {};
            }
            schema = schema[key];
        }
        schema[path[path.length - 1]] = value;
    }

    function updateUI() {
        if (!gpsState || !gpsTableBody || !map || !marker) return;

        // Update Map
        const lat = gpsState.geometry?.coordinates?.[1];
        const lon = gpsState.geometry?.coordinates?.[0];
        if (lat !== undefined && lon !== undefined) {
            const latLng = [lat, lon];
            marker.setLatLng(latLng);
            map.setView(latLng, map.getZoom());
        }

        // Update Table
        if (gpsState.properties) {
            updateGpsTable(gpsState.properties, gpsTableBody);
        }

        // Update Skyview
        if (gpsState.properties?.SV) {
            updateSkyviewChart(gpsState.properties.SV);
        }
    }

    const debouncedUpdateUI = _.debounce(updateUI, 200);

    // --- NATS Connection ---
    ConnectionManager.subscribe('gps.data.>', (m) => {
        const subjectParts = m.subject.split('.').slice(2); // Remove 'gps.data'
        const data = ConnectionManager.jsonCodec.decode(m.data);
        setNestedValue(gpsState, subjectParts, data.value);
        debouncedUpdateUI();
    }).then(sub => {
        gpsSub = sub;
    });
}

function updateGpsTable(properties, tableBody) {
    tableBody.innerHTML = ''; // Clear existing table rows
    const flattenObject = (obj, prefix = '') => {
        const result = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const newKey = prefix ? `${prefix}.${key}` : key;
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    Object.assign(result, flattenObject(obj[key], newKey));
                } else if (key !== 'SV') {
                    result[newKey] = obj[key];
                }
            }
        }
        return result;
    };
    const flatProps = flattenObject(properties);
    for (const [key, value] of Object.entries(flatProps)) {
        let displayValue = value;
        if (typeof value === 'object' && value !== null && value.type === 'Buffer') {
            displayValue = String.fromCharCode.apply(null, value.data);
        } else if (Array.isArray(value)) {
            displayValue = JSON.stringify(value);
        }
        const row = document.createElement('tr');
        row.innerHTML = `<td>${key}</td><td>${displayValue}</td>`;
        tableBody.appendChild(row);
    }
}

function getSnrColor(snr) {
    if (snr >= 40) return 'green';
    if (snr >= 30) return 'yellow';
    if (snr > 0) return 'red';
    return 'grey';
}

function updateSkyviewChart(svData) {
    const satellites = svData.SV.filter(s => s.SV_Id > 0 && s.SV_Elevation > 0);
    const trace = {
        r: satellites.map(s => 90 - s.SV_Elevation),
        theta: satellites.map(s => s.SV_Azimuth),
        customdata: satellites.map(s => s.SV_SNR),
        mode: 'markers+text',
        text: satellites.map(s => s.SV_Id),
        textposition: 'top center',
        marker: {
            color: satellites.map(s => getSnrColor(s.SV_SNR)),
            size: 15,
            symbol: 'circle'
        },
        hovertemplate: "r=%{r} t=%{theta} snr=%{customdata}",
        type: 'scatterpolar'
    };
    if(skyviewDiv) Plotly.react(skyviewDiv, [trace], skyviewDiv.layout);
}

function cleanupGpsPage() {
    console.log("Cleaning up GPS page...");
    if (gpsSub) {
        gpsSub.unsubscribe();
        gpsSub = null;
    }
    if (skyviewDiv) {
        Plotly.purge(skyviewDiv);
        skyviewDiv = null;
    }
    if (map) {
        map.remove();
        map = null;
    }
}

window.initGpsPage = initGpsPage;
window.cleanupGpsPage = cleanupGpsPage;
