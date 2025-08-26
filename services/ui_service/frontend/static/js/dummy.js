import ConnectionManager from './connection_manager.js';

// Module-level state variables
let dummySub;
let dummyDataElement;
let resetButton;

/**
 * Event handler for the reset button click.
 */
function handleResetClick() {
    console.log('Sending reset_counter command to dummy_service...');
    const command = {
        command: 'reset_counter'
    };
    // Publish the command using the shared ConnectionManager
    ConnectionManager.publish('commands.dummy_service', command);
}

/**
 * Initializes the Dummy page elements and subscriptions.
 */
function initDummyPage() {
    console.log("Initializing Dummy page...");

    // 1. Get references to UI elements
    dummyDataElement = document.getElementById('dummy-data');
    resetButton = document.getElementById('reset-dummy-counter');

    if (!dummyDataElement || !resetButton) {
        console.error("Dummy page UI elements not found! Cannot initialize page.");
        return;
    }

    // 2. Set up NATS subscription for dummy data
    ConnectionManager.subscribe('dummy.data', (m) => {
        const data = ConnectionManager.jsonCodec.decode(m.data);
        if (dummyDataElement) {
            // Update the UI with the received data
            dummyDataElement.textContent = JSON.stringify(data, null, 2);
        }
    }).then(sub => {
        // Store the subscription object so we can unsubscribe later
        dummySub = sub;
    });

    // 3. Add event listener for the reset button
    resetButton.addEventListener('click', handleResetClick);
}

/**
 * Cleans up resources used by the Dummy page.
 */
function cleanupDummyPage() {
    console.log("Cleaning up Dummy page...");

    // 1. Unsubscribe from NATS to prevent memory leaks
    if (dummySub) {
        dummySub.unsubscribe();
        dummySub = null;
    }

    // 2. Remove event listener from the button
    if (resetButton) {
        resetButton.removeEventListener('click', handleResetClick);
        resetButton = null;
    }

    // 3. Clear references to DOM elements
    dummyDataElement = null;
}

// Expose the init and cleanup functions to the global window object
// so that app.js can call them when navigating between pages.
window.initDummyPage = initDummyPage;
window.cleanupDummyPage = cleanupDummyPage;
