// $(document).ready(function() {
// });

// Initialize DataTable
// var table = $('#dataTable').DataTable();

// Initialize Leaflet map
var map = L.map('map').setView([51.505, -0.09], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);
var geoJSONLayer = L.geoJSON().addTo(map);

// WebSocket connection
const url_gps = "ws://" + window.location.host + "/ws_gps";
let ws_gps;

const url_data = "ws://" + window.location.host + "/ws_data";
let ws_data;

const connectionStatus = document.getElementById('connection-status');

function connect() {
    ws_gps = new WebSocket(url_gps);
    ws_data = new WebSocket(url_data);

    ws_gps.onopen = function() {
        console.log('ws_gps connection opened');
        connectionStatus.textContent = 'Connected';
        connectionStatus.style.color = 'green';
    };

    ws_data.onopen = function() {
        console.log('ws_data connection opened');
        connectionStatus.textContent = 'Connected';
        connectionStatus.style.color = 'green';
    };

    ws_gps.onmessage = function(event) {
        var data = JSON.parse(event.data);
        // console.log("ws_gps onmessage =" + JSON.stringify(data));

        // Update table
        // table.row.add([data.column1, data.column2]).draw(false);

        // Update map
        if (data) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    };

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

// Handle incoming messages
ws_data.onmessage = function(event) {
    // Parse the incoming message
    const data = JSON.parse(event.data);
    // console.log("buf="+ws_data.bufferedAmount)
    // console.log(JSON.stringify(data))


    // Check if the name already exists in the cache
    if (! nameCache.has(data.name)) {
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
    else {
        // Nothing to add in table
    }

    // Always store data value in cache
    nameCache.set(data.name, data.value);

    // Will be displayed by periodic function.
    // updateDisplay();
};

    // Handle WebSocket errors
    ws_data.onerror = function(error) {
        console.error('ws_data error:', error);
        connectionStatus.textContent = 'Connection Error';
        connectionStatus.style.color = 'red';
    };

    ws_gps.onerror = function(error) {
        console.error('ws_gps error:', error);
        connectionStatus.textContent = 'Connection Error';
        connectionStatus.style.color = 'red';
    };

    // Handle WebSocket close
    ws_data.onclose = function(event) {
        console.log('ws_data connection closed:', event);
        connectionStatus.textContent = 'Disconnected. Retrying...';
        connectionStatus.style.color = 'orange';
        setTimeout(connect, 5000); // Try to reconnect every 5 seconds
    };

    ws_gps.onclose = function(event) {
        console.log('ws_gps connection closed:', event);
        connectionStatus.textContent = 'Disconnected. Retrying...';
        connectionStatus.style.color = 'orange';
        setTimeout(connect, 5000); // Try to reconnect every 5 seconds
    };
}

connect();
