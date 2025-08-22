import ConnectionManager from './connection_manager.js';

let appLoggerSub;
let loggerState;
let startTime;
let startPosition;
let isRecording = false;
let currentPath = "";

async function initAppLoggerPage() {
    console.log("Initializing App Logger page...");

    // --- DOM Elements & Listeners ---
    const toggleRecordingButton = document.getElementById('toggleRecording-app-logger');
    const fileTableBody = document.querySelector('#app-filenameTable tbody');
    loggerState = document.getElementById('app-logger-state');
    startTime = document.getElementById('start-time');
    startPosition = document.getElementById('start-position');

    toggleRecordingButton.addEventListener('click', onToggleRecording);
    fileTableBody.addEventListener('click', onFileTableClick);

    // --- NATS Connections ---
    ConnectionManager.subscribe('app_logger.status', (m) => {
        onAppLoggerMessage(m);
    }).then(sub => {
        appLoggerSub = sub;
    });

    // --- Initial Load ---
    fetchAndDisplayFiles("");
}

// --- Event Handlers ---
function onToggleRecording() {
    isRecording = !isRecording;
    const command = isRecording ? 'start' : 'stop';
    ConnectionManager.publishJson('commands.app_logger_service', { command: command });

    const button = document.getElementById('toggleRecording-app-logger');
    const spinner = document.getElementById('recorderSpin-app-logger');
    button.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
    spinner.style.display = isRecording ? "flex" : "none";

    if (!isRecording) {
        setTimeout(() => fetchAndDisplayFiles(currentPath), 1000);
    }
}

function onFileTableClick(e) {
    if (e.target.classList.contains('dir-link')) {
        const path = e.target.dataset.path;
        fetchAndDisplayFiles(path);
    }
    if (e.target.classList.contains('file-link')) {
        const path = e.target.dataset.path;
        const file = e.target.dataset.file;
        openFile(file, path);
    }
}

function onAppLoggerMessage(m) {
    const data = ConnectionManager.jsonCodec.decode(m.data);
    console.log("Received data from app_logger.status:", data);

    isRecording = data.isRunning;
    // updateUI();

    if (isRecording) {
        loggerState.textContent = 'Running';
        startTime.textContent = new Date(data.startDate).toLocaleString();
        if (data.startPosition && data.startPosition.geometry) {
            const coords = data.startPosition.geometry.coordinates;
            startPosition.textContent = `Lat: ${coords[1].toFixed(6)}, Lon: ${coords[0].toFixed(6)}`;
        } else {
            startPosition.textContent = 'N/A';
        }
    } else {
        loggerState.textContent = 'Stopped';
        startTime.textContent = 'N/A';
        startPosition.textContent = 'N/A';
        // Refresh file list
        // window.location.reload();
    }
};



// --- API and Display Functions ---
async function fetchAndDisplayFiles(path) {
    currentPath = path;
    const currentPathHeader = document.getElementById('app-logger-current-path');
    const fileTableBody = document.querySelector('#app-filenameTable tbody');

    currentPathHeader.textContent = `Contenu du dossier : /${path}`;
    fileTableBody.innerHTML = '<tr><td colspan="3">Loading...</td></tr>';

    try {
        const response = await fetch(`/api/files/app_logger/${path}`);
        const data = await response.json();
        fileTableBody.innerHTML = '';

        if (path) {
            const parentPath = path.substring(0, path.lastIndexOf('/'));
            fileTableBody.insertAdjacentHTML('beforeend', `<tr><td class="dir-link" data-path="${parentPath}">..</td><td></td><td></td></tr>`);
        }

        data.contents.forEach(item => {
            if (item.type === 'dir') {
                fileTableBody.insertAdjacentHTML('beforeend', `<tr><td class="dir-link" data-path="${path ? path + '/' : ''}${item.name}">${item.name}/</td><td></td><td></td></tr>`);
            } else {
                const b64path = btoa((path ? path + '/' : '') + item.name);
                fileTableBody.insertAdjacentHTML('beforeend', `<tr class="file-row" data-ext="${item.name.split('.').pop()}"><td class="file-link" data-path="${path}" data-file="${item.name}">${item.name}</td><td>${formatFileSize(item.size)}</td><td><a href="/api/download/app_logger/${b64path}" class="download-btn">⬇️</a></td></tr>`);
            }
        });
    } catch (error) {
        console.error("Error fetching file list:", error);
        fileTableBody.innerHTML = `<tr><td colspan="3">Error fetching file list.</td></tr>`;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function openFile(file, folder) {
    console.log("Opening file : "+file);

    const logContent = document.getElementById('app-log-content');

    fetch(`/api/file/app_logger/${file}`)
        .then(response => response.json())
        .then(data => {
            logContent.textContent = JSON.stringify(data, null, 2);
        })
        .catch(error => {
            console.error('Error fetching log content:', error);
            logContent.textContent = 'Error loading log content.';
        });
}



function cleanupAppLoggerPage() {
    console.log("Cleaning up App Logger page...");
    if (appLoggerSub) {
        appLoggerSub.unsubscribe();
    }

    const toggleRecordingButton = document.getElementById('toggleRecording-app-logger');
    const fileTableBody = document.querySelector('#filenameTable tbody');
    if (toggleRecordingButton) toggleRecordingButton.removeEventListener('click', onToggleRecording);
    if (fileTableBody) fileTableBody.removeEventListener('click', onFileTableClick);
}

window.initAppLoggerPage = initAppLoggerPage;
window.cleanupAppLoggerPage = cleanupAppLoggerPage;
