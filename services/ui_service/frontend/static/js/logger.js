import ConnectionManager from './connection_manager.js';

let convertSub;
let isRecording = false;
let currentPath = "";

function initLoggerPage() {
    console.log("Initializing Logger page...");

    // --- NATS Connections ---
    ConnectionManager.subscribe('conversion.results', (m) => {
        onConvertMessage(m);
    }).then(sub => {
        convertSub = sub;
    });

    // --- DOM Elements & Listeners ---
    const toggleRecordingButton = document.getElementById('toggleRecording-logger');
    const fileTableBody = document.querySelector('#filenameTable tbody');
    const fileTableHeader = document.querySelector('#filenameTable thead tr');

    fileTableHeader.innerHTML = '<th>Nom</th><th>Taille</th><th>Status</th><th>Download</th>';

    toggleRecordingButton.addEventListener('click', onToggleRecording);
    fileTableBody.addEventListener('click', onFileTableClick);

    // --- Initial Load ---
    fetchAndDisplayFiles("");
}

// --- Event Handlers ---
function onToggleRecording() {
    isRecording = !isRecording;
    const command = isRecording ? 'startRecording' : 'stopRecording';
    ConnectionManager.publishJson('commands.can_bus_service', { command });

    const button = document.getElementById('toggleRecording-logger');
    const spinner = document.getElementById('recorderSpin-logger');
    button.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
    spinner.style.display = isRecording ? "flex" : "none";

    if (!isRecording) {
        setTimeout(() => fetchAndDisplayFiles(currentPath), 1000);
    }
}

function onFileTableClick(e) {
    const target = e.target;
    if (target.classList.contains('dir-link')) {
        fetchAndDisplayFiles(target.dataset.path);
    } else if (target.classList.contains('file-link')) {
        const path = target.dataset.path;
        const file = target.dataset.file;
        const status = target.closest('tr').dataset.status;
        triggerConversion(file, path, status);
    } else if (target.classList.contains('status-icon')) {
        const status = target.dataset.status;
        if (status === 'converted') {
            const path = target.dataset.path;
            const filename = target.dataset.filename;
            downloadAndDisplayPlot(filename, path);
        }
    }
}

function onConvertMessage(m) {
    const data = ConnectionManager.jsonCodec.decode(m.data);
    const filename = data.filename;
    const statusCell = document.querySelector(`tr[data-filename="${filename}"] .status-cell`);

    if (!statusCell) return;

    switch (data.status) {
        case "started":
            statusCell.innerHTML = getStatusIcon("converting", filename);
            break;
        case "success":
            statusCell.innerHTML = getStatusIcon("converted", filename, currentPath);
            break;
        case "error":
            statusCell.innerHTML = getStatusIcon("error", filename);
            alert(`Error converting ${filename}: ${data.message}`);
            break;
        case "already_converted":
            statusCell.innerHTML = getStatusIcon("converted", filename, currentPath);
            alert(`${filename} is already converted. Click on the file name to force a new conversion.`);
            break;
        case "busy":
            alert("Converter service is busy. Please try again later.");
            break;
    }
}

// --- API and Display Functions ---
async function fetchAndDisplayFiles(path) {
    currentPath = path;
    const currentPathHeader = document.getElementById('logger-current-path');
    const fileTableBody = document.querySelector('#filenameTable tbody');

    currentPathHeader.textContent = `Contenu du dossier : /${path}`;
    fileTableBody.innerHTML = `<tr><td colspan="4">Loading...</td></tr>`;

    try {
        const response = await fetch(`/api/files/logger/${path}`);
        const data = await response.json();
        fileTableBody.innerHTML = '';

        if (path) {
            const parentPath = path.substring(0, path.lastIndexOf('/'));
            fileTableBody.insertAdjacentHTML('beforeend', `<tr><td class="dir-link" data-path="${parentPath}">..</td><td></td><td></td><td></td></tr>`);
        }

        data.contents.forEach(item => {
            if (item.type === 'dir') {
                fileTableBody.insertAdjacentHTML('beforeend', `<tr><td class="dir-link" data-path="${path ? path + '/' : ''}${item.name}">${item.name}/</td><td></td><td></td><td></td></tr>`);
            } else {
                const b64path = btoa((path ? path + '/' : '') + item.name);
                const row = `<tr class="file-row" data-filename="${item.name}" data-status="${item.status}" data-ext="${item.name.split('.').pop()}">
                    <td class="file-link" data-path="${path}" data-file="${item.name}">${item.name}</td>
                    <td>${formatFileSize(item.size)}</td>
                    <td class="status-cell">${getStatusIcon(item.status, item.name, path)}</td>
                    <td><a href="/api/download/logger/${b64path}" class="download-btn">⬇️</a></td>
                </tr>`;
                fileTableBody.insertAdjacentHTML('beforeend', row);
            }
        });
    } catch (error) {
        console.error("Error fetching file list:", error);
        fileTableBody.innerHTML = `<tr><td colspan="4">Error fetching file list.</td></tr>`;
    }
}

function getStatusIcon(status, filename, path) {
    const jsonFilename = filename.replace('.blf', '.json');
    const fullPath = path ? `${path}/${jsonFilename}` : jsonFilename;
    switch (status) {
        case 'not_converted':
            return '<span>⚪ Not converted</span>';
        case 'converted':
            return `<span class="status-icon" data-status="converted" data-filename="${fullPath}" data-path="${path}" style="cursor:pointer;">🟢 Converted</span>`;
        case 'converting':
            return '<span><div class="recorderSpin" style="display: flex;"></div> Converting...</span>';
        case 'error':
            return '<span>🔴 Error</span>';
        default:
            return '<span>❓ Unknown</span>';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function triggerConversion(file, folder, status) {
    if (status === 'converted') {
        if (confirm(`File ${file} is already converted. Do you want to start a new conversion?`)) {
            convertFile(file, folder, true);
        }
    } else {
        convertFile(file, folder, false);
    }
}

async function convertFile(file, folder, force = false) {
    const plotlyPanel = document.getElementById('plotly-panel');
    const loader = document.getElementById('loader');
    plotlyPanel.style.display = "none";
    plotlyPanel.innerHTML = '';

    const statusCell = document.querySelector(`tr[data-filename="${file}"] .status-cell`);
    if (statusCell) {
        statusCell.innerHTML = getStatusIcon('converting', file);
    }

    try {
        await fetch("/api/convert", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: file, folder: folder, force: force }),
        });
    } catch (error) {
        console.error("Error calling /api/convert endpoint:", error);
        if (statusCell) {
            statusCell.innerHTML = getStatusIcon('error', file);
        }
    }
}

async function downloadAndDisplayPlot(filename, path) {
    const plotlyPanel = document.getElementById('plotly-panel');
    const loader = document.getElementById('loader');
    const logStatus = document.getElementById('log-status');

    plotlyPanel.style.display = "none";
    plotlyPanel.innerHTML = '';
    loader.style.display = "flex";
    logStatus.innerHTML = `Loading ${filename}...`;

    try {
        const response = await fetch(`/api/converted-files/${filename}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        loader.style.display = "none";
        logStatus.innerHTML = filename;
        displayPlot(data);
        plotlyPanel.style.display = "flex";
    } catch (error) {
        console.error("Error fetching or displaying plot:", error);
        loader.style.display = "none";
        logStatus.innerHTML = `Error loading ${filename}.`;
    }
}

function displayPlot(data) {
    const plotlyPanel = document.getElementById('plotly-panel');
    plotlyPanel.innerHTML = '';
    const plots = {};
    data.forEach((series) => {
        let [prefix, part, sig] = series.name.split('_');
        if (!sig) { sig = "Others"; }
        if (!plots[sig]) {
            plots[sig] = { traces: [], title: sig, idx: 1 };
        }
        const trace = { x: series.timestamps, y: series.values, type: 'scatter', mode: 'lines', name: series.name, yaxis: 'y' + plots[sig].idx };
        plots[sig].idx++;
        plots[sig].traces.push(trace);
    });
    Object.keys(plots).forEach((sig) => {
        const plotDiv = document.createElement('div');
        plotDiv.className = 'plotly-log-graph';
        plotlyPanel.appendChild(plotDiv);
        const layout = { title: { text: plots[sig].title }, autosize: true, automargin: true, xaxis: { rangeslider: { visible: false }, type: 'date', hovermode:'closest', showspikes : true, spikemode  : 'across', spikesnap : 'cursor', spikethickness:1, showline:true, showgrid:true }, yaxis: { fixedrange: false }, grid: { rows: plots[sig].traces.length, columns: 1 }, showlegend : true, hovermode  : 'x' };
        Plotly.react(plotDiv, plots[sig].traces, layout, {responsive: true});
    });
}

function cleanupLoggerPage() {
    console.log("Cleaning up Logger page...");
    if (convertSub) {
        convertSub.unsubscribe();
    }

    const toggleRecordingButton = document.getElementById('toggleRecording-logger');
    const fileTableBody = document.querySelector('#filenameTable tbody');
    if (toggleRecordingButton) toggleRecordingButton.removeEventListener('click', onToggleRecording);
    if (fileTableBody) fileTableBody.removeEventListener('click', onFileTableClick);
}

window.initLoggerPage = initLoggerPage;
window.cleanupLoggerPage = cleanupLoggerPage;
