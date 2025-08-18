/**
 * manager.js
 *
 * This script handles the service manager page, which allows users to view
 * the status of all microservices, start, stop, and restart them, and view their logs.
 */
function initializeManagerPage() {
    // --- DOM Elements ---
    const statusGrid = document.getElementById('status-grid');
    const stopAllBtn = document.getElementById('stop-all-btn');
    const restartAllBtn = document.getElementById('restart-all-btn');

    // --- Modal Elements ---
    const stopAllModal = document.getElementById('stop-all-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const cancelStopAllBtn = document.getElementById('cancel-stop-all-btn');
    const confirmStopAllBtn = document.getElementById('confirm-stop-all-btn');

    // --- Log Viewer Elements ---
    const logModal = document.getElementById('log-modal');
    const logServiceName = document.getElementById('log-service-name');
    const logContent = document.getElementById('log-content');
    const closeLogModalBtn = document.getElementById('close-log-modal-btn');
    let logInterval; // To hold the interval for log fetching

    // --- WebSocket Logic ---

    /**
     * Handles incoming messages from the 'manager' channel.
     * @param {object} data - The service status data from the backend.
     */
    const handleManagerMessage = (data) => {
        updateStatusGrid(data);
    };

    /**
     * Sends a command to the backend manager service.
     * @param {string} command - The command to send (e.g., 'start_service').
     * @param {object} payload - Additional data for the command.
     */
    const sendCommand = (command, payload = {}) => {
        const message = {
            channel: 'manager',
            data: { command, ...payload }
        };
        ConnectionManager.send(message);
    };

    /**
     * Requests the initial status of all services when the WebSocket connects.
     */
    const onWsOpen = () => {
        sendCommand('get_status', {});
    };

    // Register WebSocket handlers.
    ConnectionManager.register('manager', handleManagerMessage);
    ConnectionManager.register('open', onWsOpen);

    // If the connection is already open, request status immediately.
    if (ConnectionManager.connected) {
        onWsOpen();
    }

    // --- UI Rendering ---

    /**
     * Returns the appropriate CSS class for a given service status.
     * @param {string} status - The status of the service.
     * @returns {string} The CSS class name.
     */
    function getStatusClass(status) {
        switch (status) {
            case 'running': return 'status-running';
            case 'stopped': return 'status-stopped';
            case 'stopping': return 'status-restarting';
            case 'restarting': return 'status-restarting';
            case 'crashed': return 'status-crashed';
            case 'error': return 'status-crashed';
            default: return 'status-unknown';
        }
    }

    /**
     * Renders the service status cards in the grid.
     * @param {Array} services - An array of service objects.
     */
    function updateStatusGrid(services) {
        if (!statusGrid) return; // Don't try to render if the element isn't on the page.
        statusGrid.innerHTML = '';
        if (!services || services.length === 0) {
            statusGrid.innerHTML = '<p>No services found or status not yet available.</p>';
            return;
        }
        services.sort((a, b) => a.name.localeCompare(b.name)).forEach(service => {
            const card = document.createElement('div');
            card.className = 'service-card';
            card.innerHTML = `
                <div class="card-header">
                    <h3>${service.name}</h3>
                    <span class="status-badge ${getStatusClass(service.status)}">${service.status}</span>
                </div>
                <div class="card-body">
                    <p><strong>PID:</strong> ${service.pid || 'N/A'}</p>
                    <p><strong>Restarts:</strong> ${service.restart_count}</p>
                </div>
                <div class="card-footer">
                    <button class="start-btn" ${service.status === 'running' ? 'disabled' : ''}>Start</button>
                    <button class="stop-btn" ${service.status !== 'running' ? 'disabled' : ''}>Stop</button>
                    <button class="restart-btn" ${service.status !== 'running' ? 'disabled' : ''}>Restart</button>
                    <button class="logs-btn">Logs</button>
                </div>
            `;
            // Add event listeners for the service action buttons.
            card.querySelector('.start-btn').addEventListener('click', () => sendCommand('start_service', { service_name: service.name }));
            card.querySelector('.stop-btn').addEventListener('click', () => sendCommand('stop_service', { service_name: service.name }));
            card.querySelector('.restart-btn').addEventListener('click', () => sendCommand('restart_service', { service_name: service.name }));
            card.querySelector('.logs-btn').addEventListener('click', () => openLogModal(service.name));

            statusGrid.appendChild(card);
        });
    }

    // --- Global Action Event Listeners ---
    if (restartAllBtn) restartAllBtn.addEventListener('click', () => sendCommand('restart_all'));
    if (stopAllBtn) stopAllBtn.addEventListener('click', () => {
        stopAllModal.style.display = 'block';
        document.body.classList.add('modal-open');
    });

    // --- Modal Logic ---
    function closeStopAllModal() {
        if (stopAllModal) stopAllModal.style.display = 'none';
        document.body.classList.remove('modal-open');
    }

    if (closeModalBtn) closeModalBtn.addEventListener('click', closeStopAllModal);
    if (cancelStopAllBtn) cancelStopAllBtn.addEventListener('click', closeStopAllModal);
    if (confirmStopAllBtn) confirmStopAllBtn.addEventListener('click', () => {
        sendCommand('stop_all');
        closeStopAllModal();
    });

    // --- Log Viewer Logic ---
    function openLogModal(serviceName) {
        if (!logModal) return;
        logServiceName.textContent = serviceName;
        logContent.textContent = 'Loading logs...';
        logModal.style.display = 'block';
        document.body.classList.add('modal-open');

        fetchLogContent(serviceName);
        // Refresh logs periodically.
        logInterval = setInterval(() => fetchLogContent(serviceName), 2000);
    }

    function closeLogModal() {
        if (!logModal) return;
        logModal.style.display = 'none';
        clearInterval(logInterval);
        logContent.textContent = '';
        document.body.classList.remove('modal-open');
    }

    if (closeLogModalBtn) closeLogModalBtn.addEventListener('click', closeLogModal);

    async function fetchLogContent(serviceName) {
        try {
            const response = await fetch(`/api/logs/${serviceName}`);
            if (!response.ok) {
                logContent.textContent = 'Error fetching logs.';
                return;
            }
            const logs = await response.text();
            logContent.textContent = logs || 'Log file is empty or does not exist.';
            // Auto-scroll to the bottom.
            logContent.parentElement.scrollTop = logContent.parentElement.scrollHeight;
        } catch (error) {
            console.error('Error fetching logs:', error);
            logContent.textContent = 'Could not connect to server to fetch logs.';
        }
    }

    // Close modals if the user clicks outside of them.
    window.onclick = function(event) {
        if (event.target == stopAllModal) closeStopAllModal();
        if (event.target == logModal) closeLogModal();
    }
}

if (typeof initializeManagerPage === 'function') {
    initializeManagerPage();
}
