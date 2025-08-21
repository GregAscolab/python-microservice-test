// --- Manager Page ---
(function(window) {
    let socket;
    let logInterval;

    function initManagerPage() {
        console.log("Initializing Manager page...");

        // --- DOM Elements & Listeners ---
        const restartAllBtn = document.getElementById('restart-all-btn');
        const stopAllBtn = document.getElementById('stop-all-btn');
        const statusGrid = document.getElementById('status-grid');
        const closeModalBtn = document.getElementById('close-modal-btn');
        const cancelStopAllBtn = document.getElementById('cancel-stop-all-btn');
        const confirmStopAllBtn = document.getElementById('confirm-stop-all-btn');
        const closeLogModalBtn = document.getElementById('close-log-modal-btn');

        restartAllBtn.addEventListener('click', onRestartAll);
        stopAllBtn.addEventListener('click', onStopAll);
        statusGrid.addEventListener('click', onStatusGridClick);
        closeModalBtn.addEventListener('click', closeStopAllModal);
        cancelStopAllBtn.addEventListener('click', closeStopAllModal);
        confirmStopAllBtn.addEventListener('click', onConfirmStopAll);
        closeLogModalBtn.addEventListener('click', closeLogModal);
        window.addEventListener('click', onWindowClick);

        // --- WebSocket Logic ---
        socket = ConnectionManager.getSocket('/ws_manager');
        socket.addEventListener('open', onSocketOpen);
        socket.onmessage = onSocketMessage;
    }

    // --- Event Handlers ---
    function onSocketOpen(event) {
        console.log("Manager WebSocket connection established.");
        sendCommand('get_status', {});
    }

    function onSocketMessage(event) {
        const services = JSON.parse(event.data);
        updateStatusGrid(services);
    }

    function onRestartAll() { sendCommand('restart_all'); }
    function onStopAll() {
        document.getElementById('stop-all-modal').style.display = 'flex';
        document.body.classList.add('modal-open');
    }
    function onConfirmStopAll() {
        sendCommand('stop_all');
        closeStopAllModal();
    }
    function onStatusGridClick(e) {
        const button = e.target;
        const serviceName = button.closest('.service-card')?.dataset.service;
        if (!serviceName) return;

        if (button.classList.contains('start-btn')) sendCommand('start_service', { service_name: serviceName });
        if (button.classList.contains('stop-btn')) sendCommand('stop_service', { service_name: serviceName });
        if (button.classList.contains('restart-btn')) sendCommand('restart_service', { service_name: serviceName });
        if (button.classList.contains('logs-btn')) openLogModal(serviceName);
    }
    function onWindowClick(event) {
        if (event.target == document.getElementById('stop-all-modal')) closeStopAllModal();
        if (event.target == document.getElementById('log-modal')) closeLogModal();
    }

    // --- UI & Logic Functions ---
    function sendCommand(command, payload = {}) {
        const message = { command, ...payload };
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message));
        } else {
            console.error("Manager WebSocket is not open. Cannot send command.");
        }
    }

    function updateStatusGrid(services) {
        const statusGrid = document.getElementById('status-grid');
        statusGrid.innerHTML = '';
        if (!services || services.length === 0) {
            statusGrid.innerHTML = '<p>No services found or status not yet available.</p>';
            return;
        }
        services.sort((a, b) => a.name.localeCompare(b.name)).forEach(service => {
            const card = document.createElement('div');
            card.className = 'service-card';
            card.dataset.service = service.name;

            const status_class = {
                'running': 'status-running', 'stopped': 'status-stopped',
                'stopping': 'status-restarting', 'restarting': 'status-restarting',
                'crashed': 'status-crashed', 'error': 'status-crashed'
            }[service.status] || 'status-unknown';

            card.innerHTML = `
                <div class="card-header">
                    <h3>${service.name}</h3>
                    <span class="status-badge ${status_class}">${service.status}</span>
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
            statusGrid.appendChild(card);
        });
    }

    function closeStopAllModal() {
        document.getElementById('stop-all-modal').style.display = 'none';
        document.body.classList.remove('modal-open');
    }

    function openLogModal(serviceName) {
        document.getElementById('log-service-name').textContent = serviceName;
        document.getElementById('log-content').textContent = 'Loading logs...';
        document.getElementById('log-modal').style.display = 'flex';
        document.body.classList.add('modal-open');
        fetchLogContent(serviceName);
        logInterval = setInterval(() => fetchLogContent(serviceName), 2000);
    }

    function closeLogModal() {
        document.getElementById('log-modal').style.display = 'none';
        if (logInterval) clearInterval(logInterval);
        document.getElementById('log-content').textContent = '';
        document.body.classList.remove('modal-open');
    }

    async function fetchLogContent(serviceName) {
        try {
            const response = await fetch(`/api/logs/${serviceName}`);
            const logContentEl = document.getElementById('log-content');
            if (!response.ok) {
                logContentEl.textContent = `Error fetching logs: ${response.statusText}`;
                return;
            }
            const logs = await response.text();
            logContentEl.textContent = logs || 'Log file is empty or does not exist.';
            logContentEl.parentElement.scrollTop = logContentEl.parentElement.scrollHeight;
        } catch (error) {
            console.error('Error fetching logs:', error);
            document.getElementById('log-content').textContent = 'Could not connect to server to fetch logs.';
        }
    }

    function cleanupManagerPage() {
        console.log("Cleaning up Manager page...");
        ConnectionManager.closeSocket('/ws_manager');
        if (logInterval) clearInterval(logInterval);
        // Remove all listeners to prevent memory leaks
        document.getElementById('restart-all-btn').removeEventListener('click', onRestartAll);
        document.getElementById('stop-all-btn').removeEventListener('click', onStopAll);
        document.getElementById('status-grid').removeEventListener('click', onStatusGridClick);
        document.getElementById('close-modal-btn').removeEventListener('click', closeStopAllModal);
        document.getElementById('cancel-stop-all-btn').removeEventListener('click', closeStopAllModal);
        document.getElementById('confirm-stop-all-btn').removeEventListener('click', onConfirmStopAll);
        document.getElementById('close-log-modal-btn').removeEventListener('click', closeLogModal);
        window.removeEventListener('click', onWindowClick);
    }

    window.initManagerPage = initManagerPage;
    window.cleanupManagerPage = cleanupManagerPage;

})(window);
