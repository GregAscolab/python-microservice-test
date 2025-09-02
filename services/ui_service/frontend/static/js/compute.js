import ConnectionManager from './connection_manager.js';

// Module-level state variables
let stateSub;
let statusSub;
let domElements = {};

/**
 * Handles incoming state messages from the compute.state.full subject.
 * @param {object} state - The full state object from the compute_service.
 */
function updateUI(state) {
    if (!state || !domElements.resultsTableBody) return;

    // Update triggers list with unregister buttons
    domElements.activeTriggers.innerHTML = '';
    if (state.triggers && state.triggers.length > 0) {
        state.triggers.forEach(triggerName => {
            const triggerSpan = document.createElement('span');
            triggerSpan.className = 'trigger-item';
            triggerSpan.textContent = triggerName;
            const unregBtn = document.createElement('button');
            unregBtn.textContent = 'x';
            unregBtn.className = 'btn-unregister btn-unregister-trigger';
            unregBtn.dataset.triggerName = triggerName;
            triggerSpan.appendChild(unregBtn);
            domElements.activeTriggers.appendChild(triggerSpan);
        });
    } else {
        domElements.activeTriggers.textContent = 'None';
    }

    // Update results table with unregister buttons
    const stateEntries = Object.entries(state.computation_state);
    domElements.resultsTableBody.innerHTML = '';
    for (const [key, value] of stateEntries) {
        const row = domElements.resultsTableBody.insertRow();
        const cellKey = row.insertCell();
        const cellValue = row.insertCell();
        const cellAction = row.insertCell();

        cellKey.textContent = key;
        cellValue.textContent = typeof value === 'number' ? value.toFixed(2) : JSON.stringify(value);

        // Add unregister button only for computed signals (which have an underscore)
        // This is a heuristic to avoid unregistering raw CAN signals etc.
        if (key.includes('_')) {
            const unregBtn = document.createElement('button');
            unregBtn.textContent = 'Unregister';
            unregBtn.className = 'btn-unregister btn-unregister-comp';
            unregBtn.dataset.outputName = key;
            cellAction.appendChild(unregBtn);
        }
    }
}

/**
 * Fetches the list of available signals and populates the dropdowns.
 */
async function fetchAvailableSignals() {
    try {
        const response = await ConnectionManager.request('commands.compute_service', { command: 'get_available_signals' });
        const data = ConnectionManager.jsonCodec.decode(response.data);

        if (data.status === 'ok' && data.signals) {
            console.log("Available signals:", data.signals);
            updateSignalDropdowns(data.signals);
        }
    } catch (err) {
        console.error("Error fetching available signals:", err);
    }
}

/**
 * Updates the signal dropdowns with a new list of signals.
 * @param {string[]} signals - An array of signal names.
 */
function updateSignalDropdowns(signals) {
    const dropdowns = [domElements.compSourceSignal, domElements.triggerSourceSignal];
    dropdowns.forEach(dropdown => {
        if (!dropdown) return;
        // Preserve the currently selected value if it still exists
        const selectedValue = dropdown.value;
        dropdown.innerHTML = ''; // Clear existing options
        signals.sort().forEach(signal => {
            const option = document.createElement('option');
            option.value = signal;
            option.textContent = signal;
            dropdown.appendChild(option);
        });
        // Restore selection
        if (signals.includes(selectedValue)) {
            dropdown.value = selectedValue;
        }
    });
}


/**
 * Initializes the Compute page elements and subscriptions.
 */
function initComputePage() {
    console.log("Initializing Compute page...");

    // 1. Get references to all DOM elements
    domElements = {
        page: document.getElementById('page-compute'),
        formRegisterComp: document.getElementById('form-register-computation'),
        formRegisterTrigger: document.getElementById('form-register-trigger'),
        compSourceSignal: document.getElementById('comp-source-signal'),
        triggerSourceSignal: document.getElementById('trigger-source-signal'),
        serviceStatus: document.getElementById('compute-service-status'),
        activeTriggers: document.getElementById('compute-active-triggers'),
        resultsTableBody: document.getElementById('compute-results-table')?.querySelector('tbody'),
    };

    if (!domElements.resultsTableBody) {
        console.error("Compute page UI elements not found! Cannot initialize page.");
        return;
    }

    // 2. Subscribe to the full state topic
    ConnectionManager.subscribe('compute.state.full', (m) => {
        const state = ConnectionManager.jsonCodec.decode(m.data);
        updateUI(state);
    }).then(sub => {
        stateSub = sub;
    });

    // 3. Subscribe to the service status topic
    ConnectionManager.subscribe('compute.status', (m) => {
        const status = ConnectionManager.jsonCodec.decode(m.data);
        if (domElements.serviceStatus) {
            domElements.serviceStatus.textContent = status.status;
        }
    }).then(sub => {
        statusSub = sub;
    });

    // 4. Fetch initial data
    fetchAvailableSignals();

    // 5. Add form submission listeners
    domElements.formRegisterComp.addEventListener('submit', handleRegisterComputation);
    domElements.formRegisterTrigger.addEventListener('submit', handleRegisterTrigger);

    // 6. Add a single click listener for unregister buttons (event delegation)
    domElements.page.addEventListener('click', handleUnregisterClick);
}

/**
 * Handles clicks on the unregister buttons.
 * @param {Event} event - The click event.
 */
async function handleUnregisterClick(event) {
    const target = event.target;
    if (target.classList.contains('btn-unregister-comp')) {
        const outputName = target.dataset.outputName;
        console.log(`Sending unregister_computation for: ${outputName}`);
        await ConnectionManager.request('commands.compute_service', {
            command: 'unregister_computation',
            args: { output_name: outputName }
        });
    } else if (target.classList.contains('btn-unregister-trigger')) {
        const triggerName = target.dataset.triggerName;
        console.log(`Sending unregister_trigger for: ${triggerName}`);
        await ConnectionManager.request('commands.compute_service', {
            command: 'unregister_trigger',
            args: { name: triggerName }
        });
    }
}

/**
 * Handles the submission of the register trigger form.
 * @param {Event} event - The form submission event.
 */
async function handleRegisterTrigger(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const formProps = Object.fromEntries(formData.entries());

    // Construct the nested payload the backend expects
    const payload = {
        command: 'register_trigger',
        args: {
            trigger: {
                name: formProps.name,
                conditions: [{
                    name: formProps.source_signal,
                    operator: formProps.operator,
                    value: parseFloat(formProps.value) // Ensure value is a number
                }],
                action: {
                    type: "publish", // Hardcoded for now, could be a form field
                    subject: `compute.alert.${formProps.name}`
                }
            }
        }
    };

    console.log("Sending register_trigger command:", payload.args);
    try {
        const response = await ConnectionManager.request('commands.compute_service', payload);
        console.log("Response from register_trigger:", ConnectionManager.jsonCodec.decode(response.data));
    } catch (err) {
        console.error("Error registering trigger:", err);
    }
}

/**
 * Handles the submission of the register computation form.
 * @param {Event} event - The form submission event.
 */
async function handleRegisterComputation(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const payload = {
        command: 'register_computation',
        args: Object.fromEntries(formData.entries())
    };

    console.log("Sending register_computation command:", payload.args);
    try {
        const response = await ConnectionManager.request('commands.compute_service', payload);
        const data = ConnectionManager.jsonCodec.decode(response.data);
        console.log("Response from register_computation:", data);
        if (data.status === 'ok') {
            // Refresh the signal list to include the new output signal
            setTimeout(fetchAvailableSignals, 500); // Give backend a moment to update state
        }
    } catch (err) {
        console.error("Error registering computation:", err);
    }
}

/**
 * Cleans up resources used by the Compute page.
 */
function cleanupComputePage() {
    console.log("Cleaning up Compute page...");

    // 1. Unsubscribe from NATS
    if (stateSub) {
        stateSub.unsubscribe();
        stateSub = null;
    }
    if (statusSub) {
        statusSub.unsubscribe();
        statusSub = null;
    }

    // 2. Remove event listeners
    if (domElements.formRegisterComp) {
        domElements.formRegisterComp.removeEventListener('submit', handleRegisterComputation);
    }
    if (domElements.formRegisterTrigger) {
        domElements.formRegisterTrigger.removeEventListener('submit', handleRegisterTrigger);
    }
    if (domElements.page) {
        domElements.page.removeEventListener('click', handleUnregisterClick);
    }

    // 3. Clear DOM element references
    domElements = {};
}

// Expose the init and cleanup functions to the global window object
// so that app.js can call them when navigating between pages.
window.initComputePage = initComputePage;
window.cleanupComputePage = cleanupComputePage;
