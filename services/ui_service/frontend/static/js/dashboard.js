// Initialize Leaflet map
var map = L.map('map').setView([51.505, -0.09], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);
var geoJSONLayer = L.geoJSON().addTo(map);

// Handle GPS data
connectionManager.addMessageListener('gps', (data) => {
    if (data) {
        geoJSONLayer.clearLayers();
        geoJSONLayer.addData(data);
        map.fitBounds(geoJSONLayer.getBounds());
    }
});

// Get the table body element
const pressureTableBody = document.querySelector('#pressureTable tbody');
const angleTableBody = document.querySelector('#angleTable tbody');

// Cache to store received names/values
const nameCache = new Map();

// Get the buttons
const toggleRecordingButton = document.getElementById('toggleRecording');
const quitButton = document.getElementById('quitButton');

// Variable to track recording state
let isRecording = false;

// Suffix to unit map
const suffToTypeMap = new Map([
  ["_b", "pressure"],
  ["_PFAng","angle"],
]);

const typeToUnitMap = new Map([
  ["pressure", "bars"],
  ["angle","deg"],
]);

// Update display according nameCache values
function updateDisplay() {
    // Loop on cache data
    for (const [name, val] of nameCache) {
        // Update the value of data in table
        const cell = document.getElementById(name + "_val");
        cell.textContent = val;
    }
}

// Period refresh of the display, based on value received and store in cache
const intervalID = setInterval(updateDisplay, 200);

// Handle incoming data messages
connectionManager.addMessageListener('data', (data) => {
    // Check if the name already exists in the cache
    if (!nameCache.has(data.name)) {
        // Create a new row
        const newRow = document.createElement('tr');
        newRow.id = data.name; // Set the id attribute based on the name

        // Create and append the Name cell
        const nameCell = document.createElement('td');
        nameCell.textContent = data.name;
        newRow.appendChild(nameCell);

        // Create and append the Value cell
        const valueCell = document.createElement('td');
        valueCell.textContent = data.value;
        valueCell.id = data.name + "_val";  // Set the id attribute based on the name
        valueCell.style.textAlign = "right";
        newRow.appendChild(valueCell);

        // look for data type
        let unit = "";
        let tableBody;
         for (let [key, value] of suffToTypeMap) {
            if (data.name.includes(key)) {
                tableBody = document.querySelector('#'+value+'Table tbody');
                unit = typeToUnitMap.get(value);
                break;
            }
            else {
                // Default table, just in case...
                tableBody = angleTableBody;
                unit = "";
            }
        }
        // Create and append the Unit cell
        const unitCell = document.createElement('td');
        unitCell.textContent = unit;
        unitCell.id = data.name + "_unit"  // Set the id attribute based on the name
        newRow.appendChild(unitCell);

        // Append the new row to the table body
        tableBody.appendChild(newRow);
    }

    // Always store data value in cache
    nameCache.set(data.name, data.value);
});
