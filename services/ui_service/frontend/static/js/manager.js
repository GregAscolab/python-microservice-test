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
    let logInterval;

    // --- WebSocket Logic ---
    const handleManagerMessage = (data) => {
        updateStatusGrid(data);
    };

    const sendCommand = (command, payload = {}) => {
        const message = {
            channel: 'manager',
            data: { command, ...payload }
        };
        console.log("Sending command:", message);
        ConnectionManager.send(message);
    };

    // Request initial status when WebSocket connection opens
    const onWsOpen = () => {
        sendCommand('get_status', {});
    };

    ConnectionManager.register('manager', handleManagerMessage);
    ConnectionManager.register('open', onWsOpen);
    // If already connected, get status immediately
    if (ConnectionManager.connected) {
        onWsOpen();
    }


    // --- UI Rendering ---
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

    function updateStatusGrid(services) {
        if (!statusGrid) return; // In case the page is not visible
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
            card.querySelector('.start-btn').addEventListener('click', () => sendCommand('start_service', { service_name: service.name }));
            card.querySelector('.stop-btn').addEventListener('click', () => sendCommand('stop_service', { service_name: service.name }));
            card.querySelector('.restart-btn').addEventListener('click', () => sendCommand('restart_service', { service_name: service.name }));
            card.querySelector('.logs-btn').addEventListener('click', () => openLogModal(service.name));

            statusGrid.appendChild(card);
        });
    }

    // --- Event Listeners ---
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
            logContent.parentElement.scrollTop = logContent.parentElement.scrollHeight;
        } catch (error) {
            console.error('Error fetching logs:', error);
            logContent.textContent = 'Could not connect to server to fetch logs.';
        }
    }

    window.onclick = function(event) {
        if (event.target == stopAllModal) {
            closeStopAllModal();
        }
        if (event.target == logModal) {
            closeLogModal();
        }
    }
}

if (typeof initializeManagerPage === 'function') {
    initializeManagerPage();
}
