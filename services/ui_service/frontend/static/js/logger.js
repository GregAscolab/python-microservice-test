import ConnectionManager from './connection_manager.js';

let convertSub;
let isRecording = false;
let currentPath = "";
let domElements = {};

function initLoggerPage() {
    console.log("Initializing Logger page...");

    domElements = {
        modal: document.getElementById('generic-confirm-modal'),
        modalTitle: document.getElementById('generic-modal-title'),
        modalText: document.getElementById('generic-modal-text'),
        modalCancelBtn: document.getElementById('generic-modal-cancel-btn'),
        modalConfirmBtn: document.getElementById('generic-modal-confirm-btn'),
    };

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

    fileTableHeader.innerHTML = '<th>Nom</th><th>Taille</th><th>Status</th><th>Actions</th>';

    toggleRecordingButton.addEventListener('click', onToggleRecording);
    fileTableBody.addEventListener('click', onFileTableClick);
    domElements.modalCancelBtn.addEventListener('click', () => domElements.modal.style.display = 'none');


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
    } else if (target.classList.contains('view-plot-btn')) {
        const convertedPath = target.dataset.convertedPath;
        downloadAndDisplayPlot(convertedPath);
    }
}

function onConvertMessage(m) {
    const data = ConnectionManager.jsonCodec.decode(m.data);
    const filename = data.filename;

    // We need to refetch to get the updated actions (like download button)
    if (data.status === "success") {
        fetchAndDisplayFiles(currentPath);
        return;
    }

    const row = document.querySelector(`tr[data-filename="${filename}"]`);
    if (!row) return;
    const statusCell = row.querySelector('.status-cell');

    switch (data.status) {
        case "started":
            statusCell.innerHTML = getStatusIcon("converting", filename);
            break;
        case "error":
            statusCell.innerHTML = getStatusIcon("error", filename);
            showConfirmationModal("Conversion Error", `Error converting ${filename}: ${data.message}`, () => {}, true);
            break;
        case "already_converted":
             // This is now handled by the UI before calling convert, but we can have a fallback
            row.dataset.status = "converted";
            statusCell.innerHTML = getStatusIcon("converted", filename, currentPath);
            break;
        case "busy":
            showConfirmationModal("Converter Busy", "Converter service is busy. Please try again later.", () => {}, true);
            // Revert status on the UI
            const originalStatus = row.dataset.status;
            statusCell.innerHTML = getStatusIcon(originalStatus, filename, currentPath);
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
                const fullPath = (path ? path + '/' : '') + item.name;
                const b64FullPath = btoa(fullPath);

                const jsonFilename = item.name.replace('.blf', '.json');
                const convertedFullPath = path ? `${path}/${jsonFilename}` : jsonFilename;
                const b64ConvertedPath = btoa(convertedFullPath);

                const row = `<tr class="file-row" data-filename="${item.name}" data-status="${item.status}" data-ext="${item.name.split('.').pop()}">
                    <td class="file-link" data-path="${path}" data-file="${item.name}">${item.name}</td>
                    <td>${formatFileSize(item.size)}</td>
                    <td class="status-cell">${getStatusIcon(item.status)}</td>
                    <td class="actions-cell">
                        <a href="/api/download/logger/${b64FullPath}" class="download-btn" title="Download BLF">⬇️ BLF</a>
                        ${item.status === 'converted' ? `
                            <a href="/api/download-converted/${b64ConvertedPath}" class="download-btn" title="Download JSON">⬇️ JSON</a>
                            <button class="view-plot-btn" data-converted-path="${convertedFullPath}">View Plot</button>
                        ` : ''}
                    </td>
                </tr>`;
                fileTableBody.insertAdjacentHTML('beforeend', row);
            }
        });
    } catch (error) {
        console.error("Error fetching file list:", error);
        fileTableBody.innerHTML = `<tr><td colspan="4">Error fetching file list.</td></tr>`;
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'not_converted':
            return '<span>⚪ Not converted</span>';
        case 'converted':
            return `<span>🟢 Converted</span>`;
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
        showConfirmationModal(
            'Re-convert File?',
            `File ${file} is already converted. Do you want to start a new conversion? This will overwrite the existing converted file.`,
            () => convertFile(file, folder, true)
        );
    } else {
        convertFile(file, folder, false);
    }
}

function showConfirmationModal(title, text, onConfirm, isAlert = false) {
    domElements.modalTitle.textContent = title;
    domElements.modalText.textContent = text;

    if (isAlert) {
        domElements.modalConfirmBtn.style.display = 'none';
        domElements.modalCancelBtn.textContent = 'Close';
    } else {
        domElements.modalConfirmBtn.style.display = 'inline-block';
        domElements.modalCancelBtn.textContent = 'Cancel';

        // Clone and replace the confirm button to remove old event listeners
        const newConfirmBtn = domElements.modalConfirmBtn.cloneNode(true);
        domElements.modalConfirmBtn.parentNode.replaceChild(newConfirmBtn, domElements.modalConfirmBtn);
        domElements.modalConfirmBtn = newConfirmBtn;

        domElements.modalConfirmBtn.onclick = () => {
            onConfirm();
            domElements.modal.style.display = 'none';
        };
    }

    domElements.modal.style.display = 'flex';
}


async function convertFile(file, folder, force = false) {
    const plotlyPanel = document.getElementById('plotly-panel');
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

async function downloadAndDisplayPlot(convertedPath) {
    const plotlyPanel = document.getElementById('plotly-panel');
    const loader = document.getElementById('loader');
    const logStatus = document.getElementById('log-status');

    plotlyPanel.style.display = "none";
    plotlyPanel.innerHTML = '';
    loader.style.display = "flex";
    logStatus.innerHTML = `Loading ${convertedPath}...`;

    try {
        const response = await fetch(`/api/converted-files/${convertedPath}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        loader.style.display = "none";
        logStatus.innerHTML = convertedPath;
        displayPlot(data);
        plotlyPanel.style.display = "flex";
    } catch (error) {
        console.error("Error fetching or displaying plot:", error);
        loader.style.display = "none";
        logStatus.innerHTML = `Error loading ${convertedPath}.`;
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
