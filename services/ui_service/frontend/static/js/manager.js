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
function getWebSocketURL(path) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}${path}`;
}

const socket = new WebSocket(getWebSocketURL('/ws_manager'));

socket.onopen = function(event) {
    console.log("Manager WebSocket connection established.");
    // Request initial status on connection
    sendCommand('get_status', {});
};

socket.onmessage = function(event) {
    const services = JSON.parse(event.data);
    updateStatusGrid(services);
};

socket.onclose = function(event) {
    console.log("Manager WebSocket connection closed.");
};

socket.onerror = function(error) {
    console.error("Manager WebSocket error:", error);
};

function sendCommand(command, payload = {}) {
    const message = { command, ...payload };
    console.log("Sending command:", message);
    socket.send(JSON.stringify(message));
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
        // Add event listeners directly to the buttons
        card.querySelector('.start-btn').addEventListener('click', () => sendCommand('start_service', { service_name: service.name }));
        card.querySelector('.stop-btn').addEventListener('click', () => sendCommand('stop_service', { service_name: service.name }));
        card.querySelector('.restart-btn').addEventListener('click', () => sendCommand('restart_service', { service_name: service.name }));
        card.querySelector('.logs-btn').addEventListener('click', () => openLogModal(service.name));

        statusGrid.appendChild(card);
    });
}

// --- Event Listeners ---
restartAllBtn.addEventListener('click', () => sendCommand('restart_all'));
stopAllBtn.addEventListener('click', () => {
    stopAllModal.style.display = 'block';
    document.body.classList.add('modal-open');
});

// --- Modal Logic ---
function closeStopAllModal() {
    stopAllModal.style.display = 'none';
    document.body.classList.remove('modal-open');
}

closeModalBtn.addEventListener('click', closeStopAllModal);
cancelStopAllBtn.addEventListener('click', closeStopAllModal);
confirmStopAllBtn.addEventListener('click', () => {
    sendCommand('stop_all');
    closeStopAllModal();
});

// --- Log Viewer Logic ---
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
    clearInterval(logInterval);
    logContent.textContent = '';
    document.body.classList.remove('modal-open');
}

closeLogModalBtn.addEventListener('click', closeLogModal);

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

// Close modal if clicking outside of it
window.onclick = function(event) {
    if (event.target == stopAllModal) {
        closeStopAllModal();
    }
    if (event.target == logModal) {
        closeLogModal();
    }
}
