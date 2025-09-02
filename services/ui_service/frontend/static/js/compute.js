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
    if (!state || !domElements.computedTableBody || !domElements.sourceTablesContainer) return;
    domElements.lastState = state;

    const allSignalKeys = new Set(Object.keys(state.computation_state || {}));
    const computedSignalsMap = new Map((state.computations || []).map(c => [c.output_name, c]));

    // Prune cache of signals that no longer exist
    for (const signalName in domElements.cellCache) {
        if (!allSignalKeys.has(signalName)) {
            domElements.cellCache[signalName].row.remove();
            delete domElements.cellCache[signalName];
        }
    }

    // Update triggers and tables
    updateTriggersList(state.triggers || [], state.computation_state || {});
    for (const [key, value] of Object.entries(state.computation_state || {})) {
        const isComputed = computedSignalsMap.has(key);
        if (domElements.cellCache[key]) {
            // Update existing cell
            domElements.cellCache[key].valueCell.textContent = typeof value === 'number' ? value.toFixed(3) : JSON.stringify(value);
        } else {
            // Create new row and cache cells
            if (isComputed) {
                const compDef = computedSignalsMap.get(key);
                const row = domElements.computedTableBody.insertRow();
                row.insertCell().textContent = key;
                const valueCell = row.insertCell();
                valueCell.textContent = typeof value === 'number' ? value.toFixed(3) : JSON.stringify(value);
                row.insertCell().textContent = compDef.computation_type;
                row.insertCell().textContent = compDef.source_signal;
                const actionCell = row.insertCell();
                const unregBtn = document.createElement('button');
                unregBtn.textContent = 'Unregister';
                unregBtn.className = 'btn-unregister btn-unregister-comp';
                unregBtn.dataset.outputName = key;
                actionCell.appendChild(unregBtn);
                domElements.cellCache[key] = { row, valueCell };
            } else {
                const groupName = getSignalGroup(key);
                const table = getOrCreateSourceTable(groupName);
                const row = table.insertRow();
                row.insertCell().textContent = key;
                const valueCell = row.insertCell();
                valueCell.textContent = typeof value === 'number' ? value.toFixed(3) : JSON.stringify(value);
                domElements.cellCache[key] = { row, valueCell };
            }
        }
    }
}

function getSignalGroup(signalName) {
    if (signalName.startsWith('can_data.')) return 'CAN Data';
    if (signalName.startsWith('digital_twin.')) return 'Digital Twin';
    return 'Other Sources';
}

function getOrCreateSourceTable(groupName) {
    if (domElements.tableCache[groupName]) {
        return domElements.tableCache[groupName];
    }
    const h5 = document.createElement('h5');
    h5.textContent = groupName;
    const table = document.createElement('table');
    table.className = 'compute-table';
    table.innerHTML = `<thead><tr><th>Source Signal</th><th>Value</th></tr></thead>`;
    const tbody = table.createTBody();
    domElements.sourceTablesContainer.appendChild(h5);
    domElements.sourceTablesContainer.appendChild(table);
    domElements.tableCache[groupName] = tbody;
    return tbody;
}

function updateTriggersList(triggers, computationState) {
    domElements.activeTriggers.innerHTML = '';
    if (triggers.length > 0) {
        triggers.forEach(trigger => {
            const triggerDiv = document.createElement('div');
            triggerDiv.className = 'trigger-item-detailed';

            const header = document.createElement('div');
            header.className = 'trigger-header';
            const statusDot = document.createElement('span');
            statusDot.className = 'trigger-status-dot';
            statusDot.style.backgroundColor = trigger.is_currently_active ? 'limegreen' : 'tomato';
            const triggerName = document.createElement('span');
            triggerName.textContent = trigger.name;
            const unregBtn = document.createElement('button');
            unregBtn.textContent = 'x';
            unregBtn.className = 'btn-unregister btn-unregister-trigger';
            unregBtn.dataset.triggerName = trigger.name;
            header.appendChild(statusDot);
            header.appendChild(triggerName);
            header.appendChild(unregBtn);

            const body = document.createElement('div');
            body.className = 'trigger-body';
            const conditions = trigger.conditions.map(c => {
                const currentValue = computationState[c.name];
                const formattedValue = typeof currentValue === 'number' ? currentValue.toFixed(2) : 'N/A';
                return `${c.name} ${c.operator} ${c.value} (current: ${formattedValue})`;
            }).join(', ');
            body.innerHTML = `<p><strong>Conditions:</strong> ${conditions}</p>
                              <p><strong>Last Event:</strong> ${trigger.last_event_timestamp ? new Date(trigger.last_event_timestamp).toLocaleTimeString() : 'None'}</p>`;

            triggerDiv.appendChild(header);
            triggerDiv.appendChild(body);
            domElements.activeTriggers.appendChild(triggerDiv);
        });
    } else {
        const p = document.createElement('p');
        p.textContent = 'No active triggers.';
        domElements.activeTriggers.appendChild(p);
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
 * Updates the signal dropdowns with a new list of signals, grouped by source.
 * @param {string[]} signals - An array of signal names.
 */
function updateSignalDropdowns(signals) {
    const groups = {
        'Computed Values': [],
        'CAN Data': [],
        'Digital Twin': [],
        'Other': []
    };

    // Categorize signals into groups
    const computedNames = new Set((domElements.lastState.computations || []).map(c => c.output_name));
    signals.forEach(signal => {
        if (computedNames.has(signal)) {
            groups['Computed Values'].push(signal);
        } else if (signal.startsWith('can_data.')) {
            groups['CAN Data'].push(signal);
        } else if (signal.startsWith('digital_twin.')) {
            groups['Digital Twin'].push(signal);
        } else {
            groups['Other'].push(signal);
        }
    });

    // Populate both searchable select components
    populateSearchableSelect(domElements.compSearchableSelect, groups);
    populateSearchableSelect(domElements.triggerSearchableSelect, groups);
}

function populateSearchableSelect(container, groups) {
    const optionsContainer = container.querySelector('.options-container');
    optionsContainer.innerHTML = ''; // Clear existing options

    for (const [groupName, signalList] of Object.entries(groups)) {
        if (signalList.length > 0) {
            const groupLabel = document.createElement('div');
            groupLabel.className = 'optgroup-label';
            groupLabel.textContent = groupName;
            optionsContainer.appendChild(groupLabel);

            signalList.sort().forEach(signal => {
                const option = document.createElement('div');
                option.className = 'option';
                option.dataset.value = signal;
                option.textContent = signal;
                optionsContainer.appendChild(option);
            });
        }
    }
}

function setupSearchableSelect(container) {
    const searchInput = container.querySelector('.search-input');
    const optionsContainer = container.querySelector('.options-container');
    const hiddenInput = container.querySelector('input[type="hidden"]');

    // Show/hide dropdown
    searchInput.addEventListener('focus', () => container.classList.add('open'));
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            container.classList.remove('open');
        }
    });

    // Filter options on search
    searchInput.addEventListener('keyup', () => {
        const filter = searchInput.value.toLowerCase();
        optionsContainer.querySelectorAll('.option').forEach(option => {
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(filter) ? '' : 'none';
        });
    });

    // Handle option selection
    optionsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('option')) {
            const value = e.target.dataset.value;
            searchInput.value = value;
            hiddenInput.value = value;
            container.classList.remove('open');
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
        configPanel: document.getElementById('compute-config-panel'),
        btnToggleConfig: document.getElementById('btn-toggle-config'),
        formRegisterComp: document.getElementById('form-register-computation'),
        formRegisterTrigger: document.getElementById('form-register-trigger'),
        compSearchableSelect: document.getElementById('searchable-select-comp'),
        triggerSearchableSelect: document.getElementById('searchable-select-trigger'),
        serviceStatus: document.getElementById('compute-service-status'),
        activeTriggers: document.getElementById('compute-active-triggers'),
        computedTableBody: document.getElementById('compute-computed-table')?.querySelector('tbody'),
        sourceTablesContainer: document.getElementById('source-tables-container'),
        modal: document.getElementById('compute-confirm-modal'),
        modalTitle: document.getElementById('compute-modal-title'),
        modalText: document.getElementById('compute-modal-text'),
        modalCancelBtn: document.getElementById('compute-modal-cancel-btn'),
        modalConfirmBtn: document.getElementById('compute-modal-confirm-btn'),
        lastState: { computations: [], triggers: [], computation_state: {} }, // Initial empty state
        cellCache: {}, // To store references to value cells <td>
        tableCache: {}, // To store references to source tables
    };

    if (!domElements.computedTableBody || !domElements.sourceTablesContainer || !domElements.modal) {
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

    // 7. Set up searchable select components
    setupSearchableSelect(domElements.compSearchableSelect);
    setupSearchableSelect(domElements.triggerSearchableSelect);

    // 8. Add listener for responsive config toggle
    domElements.btnToggleConfig.addEventListener('click', () => {
        // On wide screens, we use a different class to shrink content
        if (window.innerWidth > 1200) {
            domElements.configPanel.classList.toggle('collapsed');
        } else {
            domElements.configPanel.classList.toggle('open');
        }
    });

    // 9. Add listeners for the confirmation modal
    domElements.modalCancelBtn.addEventListener('click', () => {
        domElements.modal.style.display = 'none';
    });
}

/**
 * Handles clicks on the unregister buttons by showing a confirmation modal.
 * @param {Event} event - The click event.
 */
function handleUnregisterClick(event) {
    const target = event.target;
    let command = null;
    let args = null;
    let itemType = '';
    let itemName = '';

    if (target.classList.contains('btn-unregister-comp')) {
        itemName = target.dataset.outputName;
        itemType = 'computation';
        command = 'unregister_computation';
        args = { output_name: itemName };
    } else if (target.classList.contains('btn-unregister-trigger')) {
        itemName = target.dataset.triggerName;
        itemType = 'trigger';
        command = 'unregister_trigger';
        args = { name: itemName };
    }

    if (command) {
        showConfirmationModal(
            `Delete ${itemType}`,
            `Are you sure you want to delete the ${itemType} "${itemName}"? This action cannot be undone.`,
            () => {
                console.log(`Sending ${command} for: ${itemName}`);
                ConnectionManager.request('commands.compute_service', { command, ...args });
            }
        );
    }
}

/**
 * Shows the confirmation modal.
 * @param {string} title - The title for the modal.
 * @param {string} text - The confirmation text.
 * @param {function} onConfirm - The callback function to execute if confirmed.
 */
function showConfirmationModal(title, text, onConfirm) {
    domElements.modalTitle.textContent = title;
    domElements.modalText.textContent = text;

    // Clone and replace the confirm button to remove old event listeners
    const newConfirmBtn = domElements.modalConfirmBtn.cloneNode(true);
    domElements.modalConfirmBtn.parentNode.replaceChild(newConfirmBtn, domElements.modalConfirmBtn);
    domElements.modalConfirmBtn = newConfirmBtn;

    domElements.modalConfirmBtn.onclick = () => {
        onConfirm();
        domElements.modal.style.display = 'none';
    };

    domElements.modal.style.display = 'flex';
}

/**
 * Handles the submission of the register trigger form.
 * @param {Event} event - The form submission event.
 */
async function handleRegisterTrigger(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const formProps = Object.fromEntries(formData.entries());

    // Construct the payload with the trigger object at the top level
    const payload = {
        command: 'register_trigger',
        trigger: {
            name: formProps.name,
            conditions: [{
                name: formProps.source_signal,
                operator: formProps.operator,
                value: parseFloat(formProps.value) // Ensure value is a number
            }],
            action: {
                // By default, create actions for state changes
                on_become_active: {
                    type: "publish",
                    subject: `compute.alert.${formProps.name}.active`
                },
                on_become_inactive: {
                    type: "publish",
                    subject: `compute.alert.${formProps.name}.inactive`
                }
            }
        }
    };

    console.log("Sending register_trigger command:", payload);
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
    const formProps = Object.fromEntries(formData.entries());
    const payload = {
        command: 'register_computation',
        ...formProps // Unpack form properties into the top level of the payload
    };

    console.log("Sending register_computation command:", payload);
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
    // Note: The toggle button listener is not removed as it's an anonymous function.
    // This is acceptable as the whole page context is destroyed on navigation.

    // 3. Clear dynamically generated content from the DOM
    if (domElements.computedTableBody) domElements.computedTableBody.innerHTML = '';
    if (domElements.sourceTablesContainer) domElements.sourceTablesContainer.innerHTML = '';
    if (domElements.activeTriggers) domElements.activeTriggers.innerHTML = '';


    // 4. Clear state and caches
    domElements = {};
}

// Expose the init and cleanup functions to the global window object
// so that app.js can call them when navigating between pages.
window.initComputePage = initComputePage;
window.cleanupComputePage = cleanupComputePage;
