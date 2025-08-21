// --- Logger Page ---
(function(window) {
    let dataSocket;
    let convertSocket;
    let isRecording = false;
    let currentPath = "";

    function initLoggerPage() {
        console.log("Initializing Logger page...");

        // --- NATS Subscriptions ---
        const textEncoder = new TextEncoder();
        const textDecoder = new TextDecoder();
        NatsConnectionManager.subscribe('conversion.results', (m) => {
            onConvertMessage(JSON.parse(textDecoder.decode(m.data)));
        });

        // --- DOM Elements & Listeners ---
        const toggleRecordingButton = document.getElementById('toggleRecording-logger');
        const fileTableBody = document.querySelector('#filenameTable tbody');

        toggleRecordingButton.addEventListener('click', onToggleRecording);
        fileTableBody.addEventListener('click', onFileTableClick);

        // --- Initial Load ---
        fetchAndDisplayFiles("");
    }

    // --- Event Handlers ---
    function onToggleRecording() {
        isRecording = !isRecording;
        const command = isRecording ? 'startRecording' : 'stopRecording';
        const textEncoder = new TextEncoder();
        NatsConnectionManager.connection.publish('commands.can_bus_service', textEncoder.encode(JSON.stringify({ command })));

        const button = document.getElementById('toggleRecording-logger');
        const spinner = document.getElementById('recorderSpin-logger');
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

    function onConvertMessage(event) {
        const data = JSON.parse(event.data);
        const loader = document.getElementById('loader');
        const plotlyPanel = document.getElementById('plotly-panel');
        const logStatus = document.getElementById('log-status');

        if (data.status === "started") {
            loader.style.display = "flex";
            plotlyPanel.style.display = "none";
            logStatus.innerHTML = data.filename + ' : ' + data.status;
        } else if (data.status === "success") {
            loader.style.display = "none";
            if (Object.keys(data.data).length > 0) {
                logStatus.innerHTML = data.filename;
                displayPlot(data.data);
                plotlyPanel.style.display = "flex";
            } else {
                logStatus.innerHTML = "NO DATA in " + data.filename;
            }
        } else if (data.status === "error") {
            loader.style.display = "none";
            logStatus.innerHTML = data.filename + ' : ' + data.status;
        }
    }

    // --- API and Display Functions ---
    async function fetchAndDisplayFiles(path) {
        currentPath = path;
        const currentPathHeader = document.getElementById('logger-current-path');
        const fileTableBody = document.querySelector('#filenameTable tbody');

        currentPathHeader.textContent = `Contenu du dossier : /${path}`;
        fileTableBody.innerHTML = '<tr><td colspan="3">Loading...</td></tr>';

        try {
            const response = await fetch(`/api/logger/files/${path}`);
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
                    fileTableBody.insertAdjacentHTML('beforeend', `<tr class="file-row" data-ext="${item.name.split('.').pop()}"><td class="file-link" data-path="${path}" data-file="${item.name}">${item.name}</td><td>${formatFileSize(item.size)}</td><td><a href="/download/${b64path}" class="download-btn">⬇️</a></td></tr>`);
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
        const plotlyPanel = document.getElementById('plotly-panel');
        const loader = document.getElementById('loader');
        plotlyPanel.style.display = "none";
        plotlyPanel.innerHTML = '';
        loader.style.display = "flex";

        try {
            const response = await fetch("/convert", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: file, folder: folder }),
            });
            const result = await response.json();
            if (result.status !== "queued") {
                loader.style.display = "none";
            }
        } catch (error) {
            console.error("Error calling /convert endpoint:", error);
            loader.style.display = "none";
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
        // NATS subscriptions are managed globally by NatsConnectionManager

        const toggleRecordingButton = document.getElementById('toggleRecording-logger');
        const fileTableBody = document.querySelector('#filenameTable tbody');
        if (toggleRecordingButton) toggleRecordingButton.removeEventListener('click', onToggleRecording);
        if (fileTableBody) fileTableBody.removeEventListener('click', onFileTableClick);
    }

    window.initLoggerPage = initLoggerPage;
    window.cleanupLoggerPage = cleanupLoggerPage;

})(window);
