(function() {
    let isInitialized = false;
    let socket;
    let statusGrid, stopAllBtn, restartAllBtn, stopAllModal, closeModalBtn, cancelStopAllBtn, confirmStopAllBtn;
    let logModal, logServiceName, logContent, closeLogModalBtn, logInterval;

    function initManagerPage() {
        if (isInitialized) return;
        console.log("Initializing Manager page...");

        statusGrid = document.getElementById('status-grid');
        stopAllBtn = document.getElementById('stop-all-btn');
        restartAllBtn = document.getElementById('restart-all-btn');
        stopAllModal = document.getElementById('stop-all-modal');
        closeModalBtn = document.getElementById('close-modal-btn');
        cancelStopAllBtn = document.getElementById('cancel-stop-all-btn');
        confirmStopAllBtn = document.getElementById('confirm-stop-all-btn');
        logModal = document.getElementById('log-modal');
        logServiceName = document.getElementById('log-service-name');
        logContent = document.getElementById('log-content');
        closeLogModalBtn = document.getElementById('close-log-modal-btn');

        restartAllBtn.addEventListener('click', handleRestartAll);
        stopAllBtn.addEventListener('click', handleStopAll);
        closeModalBtn.addEventListener('click', closeStopAllModal);
        cancelStopAllBtn.addEventListener('click', closeStopAllModal);
        confirmStopAllBtn.addEventListener('click', handleConfirmStopAll);
        closeLogModalBtn.addEventListener('click', closeLogModal);
        window.addEventListener('click', outsideClickListener);

        sendCommand('get_status');
        isInitialized = true;
        console.log("Manager page initialization complete.");
    }

    function onWsMessage(event) {
        if (!isInitialized) return;
        const services = JSON.parse(event.data);
        updateStatusGrid(services);
    }

    function onSocketReconnected(event, data) {
        if (data.path === '/ws_manager') {
            console.log("Manager page detected a reconnection. Re-fetching status.");
            sendCommand('get_status');
        }
    }

    function sendCommand(command, payload = {}) {
        const message = { command, ...payload };
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message));
        } else {
            console.error("Manager WebSocket is not open. Cannot send command.");
        }
    }

    function handleRestartAll() { sendCommand('restart_all'); }
    function handleStopAll() {
        stopAllModal.style.display = 'block';
        document.body.classList.add('modal-open');
    }
    function closeStopAllModal() {
        stopAllModal.style.display = 'none';
        document.body.classList.remove('modal-open');
    }
    function handleConfirmStopAll() {
        sendCommand('stop_all');
        closeStopAllModal();
    }

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
        if (!statusGrid) return;
        statusGrid.innerHTML = '';
        if (!services || services.length === 0) {
            statusGrid.innerHTML = '<p>No services found or status not yet available.</p>';
            return;
        }
        services.sort((a, b) => a.name.localeCompare(b.name)).forEach(service => {
            const card = document.createElement('div');
            card.className = 'service-card';
            card.innerHTML = `
                <div class="card-header"><h3>${service.name}</h3><span class="status-badge ${getStatusClass(service.status)}">${service.status}</span></div>
                <div class="card-body"><p><strong>PID:</strong> ${service.pid || 'N/A'}</p><p><strong>Restarts:</strong> ${service.restart_count}</p></div>
                <div class="card-footer">
                    <button class="start-btn" ${service.status === 'running' ? 'disabled' : ''}>Start</button>
                    <button class="stop-btn" ${service.status !== 'running' ? 'disabled' : ''}>Stop</button>
                    <button class="restart-btn" ${service.status !== 'running' ? 'disabled' : ''}>Restart</button>
                    <button class="logs-btn">Logs</button>
                </div>`;
            card.querySelector('.start-btn').addEventListener('click', () => sendCommand('start_service', { service_name: service.name }));
            card.querySelector('.stop-btn').addEventListener('click', () => sendCommand('stop_service', { service_name: service.name }));
            card.querySelector('.restart-btn').addEventListener('click', () => sendCommand('restart_service', { service_name: service.name }));
            card.querySelector('.logs-btn').addEventListener('click', () => openLogModal(service.name));
            statusGrid.appendChild(card);
        });
    }

    function openLogModal(serviceName) {
        logServiceName.textContent = serviceName;
        logContent.textContent = 'Loading logs...';
        logModal.style.display = 'block';
        document.body.classList.add('modal-open');
        fetchLogContent(serviceName);
        logInterval = setInterval(() => fetchLogContent(serviceName), 2000);
    }

    function closeLogModal() {
        logModal.style.display = 'none';
        if (logInterval) clearInterval(logInterval);
        logContent.textContent = '';
        document.body.classList.remove('modal-open');
    }

    async function fetchLogContent(serviceName) {
        try {
            const response = await fetch(`/api/logs/${serviceName}`);
            if (!response.ok) {
                if (logContent) logContent.textContent = `Error fetching logs: ${response.statusText}`;
                return;
            }
            const logs = await response.text();
            if (logContent) {
                logContent.textContent = logs || 'Log file is empty or does not exist.';
                logContent.parentElement.scrollTop = logContent.parentElement.scrollHeight;
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
            if (logContent) logContent.textContent = 'Could not connect to server to fetch logs.';
        }
    }

    const outsideClickListener = (event) => {
        if (event.target == stopAllModal) closeStopAllModal();
        if (event.target == logModal) closeLogModal();
    };

    // --- Main Execution ---
    initManagerPage();
    socket = ConnectionManager.getSocket('/ws_manager', onWsMessage);
    $(document).on('socketReconnected.manager', onSocketReconnected);

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Manager page...");
        ConnectionManager.closeSocket('/ws_manager');
        $(document).off('socketReconnected.manager');
        if (logInterval) clearInterval(logInterval);
        window.removeEventListener('click', outsideClickListener);
        if (restartAllBtn) restartAllBtn.removeEventListener('click', handleRestartAll);
        if (stopAllBtn) stopAllBtn.removeEventListener('click', handleStopAll);
        if (closeModalBtn) closeModalBtn.removeEventListener('click', closeStopAllModal);
        if (cancelStopAllBtn) cancelStopAllBtn.removeEventListener('click', closeStopAllModal);
        if (confirmStopAllBtn) confirmStopAllBtn.removeEventListener('click', handleConfirmStopAll);
        if (closeLogModalBtn) closeLogModalBtn.removeEventListener('click', closeLogModal);
        isInitialized = false;
        console.log("Manager page cleanup complete.");
    };
})();
