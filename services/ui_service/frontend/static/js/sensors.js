import ConnectionManager from './connection_manager.js';

// Module-level state variables
let sensorsSub;
let sensorsDataElement;
let scanButton;

/**
 * Event handler for the scan sensors button click.
 */
function handleScanClick() {
    console.log('Sending scan command to sensors_service...');
    const command = {
        "command": 'scan_sensors'
    };
    // Publish the command using the shared ConnectionManager
    ConnectionManager.publishJson('commands.sensors_service', command);
    sensorsDataElement.textContent = "Scan started...";
}

/**
 * Initializes the sensors page elements and subscriptions.
 */
function initSensorsPage() {
    console.log("Initializing Sensors page...");

    // 1. Get references to UI elements
    sensorsDataElement = document.getElementById('sensors-data');
    scanButton = document.getElementById('scan-sensors');

    if (!sensorsDataElement || !scanButton) {
        console.error("Sensors page UI elements not found! Cannot initialize page.");
        return;
    }

    // 2. Set up NATS subscription for sensors data
    ConnectionManager.subscribe('sensors.data', (m) => {
        const data = ConnectionManager.jsonCodec.decode(m.data);
        if (sensorsDataElement) {
            // Update the UI with the received data
            sensorsDataElement.textContent = sensorsDataElement.textContent + "\n" + JSON.stringify(data, null, 2);
        }
    }).then(sub => {
        // Store the subscription object so we can unsubscribe later
        sensorsSub = sub;
    });

    // 3. Add event listener for the scan button
    scanButton.addEventListener('click', handleScanClick);    
}

/**
 * Cleans up resources used by the Sensors page.
 */
function cleanupSensorsPage() {
    console.log("Cleaning up Sensors page...");

    // 1. Unsubscribe from NATS to prevent memory leaks
    if (sensorsSub) {
        sensorsSub.unsubscribe();
        sensorsSub = null;
    }

    // 2. Remove event listener from the button
    if (scanButton) {
        scanButton.removeEventListener('click', handleScanClick);
        scanButton = null;
    }

    // 3. Clear references to DOM elements
    sensorsDataElement = null;
}

// Expose the init and cleanup functions to the global window object
// so that app.js can call them when navigating between pages.
window.initSensorsPage = initSensorsPage;
window.cleanupSensorsPage = cleanupSensorsPage;
