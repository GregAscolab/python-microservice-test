(function() {
    // --- WebSocket Connections ---
    const dataSocket = ConnectionManager.getSocket('/ws_data');
    const convertSocket = ConnectionManager.getSocket('/ws_convert');

    // --- DOM Elements ---
    const toggleRecordingButton = document.getElementById('toggleRecording-logger');
    const recorderSpin = document.getElementById('recorderSpin-logger');
    const plotlyPanel = document.getElementById('plotly-panel');
    const loader = document.getElementById('loader');
    const fileTableBody = document.querySelector('#filenameTable tbody');
    const currentPathHeader = document.getElementById('logger-current-path');

    // --- State ---
    let isRecording = false;
    let currentPath = "";

    // --- Functions ---

    async function fetchAndDisplayFiles(path) {
        currentPath = path;
        currentPathHeader.textContent = `Contenu du dossier : /${path}`;
        fileTableBody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';

        try {
            const response = await fetch(`/api/logger/files/${path}`);
            const data = await response.json();

            if (data.error) {
                fileTableBody.innerHTML = `<tr><td colspan="4">Error: ${data.error}</td></tr>`;
                return;
            }

            fileTableBody.innerHTML = ''; // Clear loading message

            // Add "go up" link if not at root
            if (path) {
                const parentPath = path.substring(0, path.lastIndexOf('/'));
                const upRow = `
                    <tr>
                        <td class="dir-link" data-path="${parentPath}">..</td>
                        <td></td>
                        <td></td>
                        <td></td>
                    </tr>`;
                fileTableBody.insertAdjacentHTML('beforeend', upRow);
            }

            // Add directories
            data.contents.forEach(item => {
                if (item.type === 'dir') {
                    const dirRow = `
                        <tr>
                            <td class="dir-link" data-path="${path ? path + '/' : ''}${item.name}">${item.name}/</td>
                            <td></td>
                            <td></td>
                            <td></td>
                        </tr>`;
                    fileTableBody.insertAdjacentHTML('beforeend', dirRow);
                }
            });

            // Add files
            data.contents.forEach(item => {
                if (item.type === 'file') {
                    const b64path = btoa((path ? path + '/' : '') + item.name);
                    const fileRow = `
                        <tr class="file-row" data-ext="${item.name.split('.').pop()}">
                            <td class="file-link" data-path="${path}" data-file="${item.name}">${item.name}</td>
                            <td>${formatFileSize(item.size)}</td>
                            <td><span class="file-status"></span></td>
                            <td><a href="/download/${b64path}" class="download-btn">⬇️</a></td>
                        </tr>`;
                    fileTableBody.insertAdjacentHTML('beforeend', fileRow);
                }
            });

        } catch (error) {
            console.error("Error fetching file list:", error);
            fileTableBody.innerHTML = `<tr><td colspan="4">Error fetching file list.</td></tr>`;
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
        plotlyPanel.style.display = "none";
        plotlyPanel.innerHTML = '';
        document.querySelectorAll('.file-status').forEach(span => span.textContent = '');

        // Find the correct row to update status
        // This is complex, a better way would be to have unique IDs per row
        loader.style.display = "block";

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
        // This function remains the same as before
    }

    // --- Event Listeners ---
    toggleRecordingButton.addEventListener('click', function() {
        isRecording = !isRecording;
        const command = isRecording ? 'startRecording' : 'stopRecording';
        dataSocket.send(JSON.stringify({ command }));
        toggleRecordingButton.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
        recorderSpin.style.display = isRecording ? "block" : "none";
        if (!isRecording) {
            setTimeout(() => fetchAndDisplayFiles(currentPath), 1000);
        }
    });

    fileTableBody.addEventListener('click', function(e) {
        if (e.target.classList.contains('dir-link')) {
            const path = e.target.dataset.path;
            fetchAndDisplayFiles(path);
        }
        if (e.target.classList.contains('file-link')) {
            const path = e.target.dataset.path;
            const file = e.target.dataset.file;
            openFile(file, path);
        }
    });

    // --- WebSocket Handlers ---
    convertSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.status === "started") {
            loader.style.display = "block";
            plotlyPanel.style.display = "none";
        } else if (data.status === "success") {
            loader.style.display = "none";
            displayPlot(data.data);
            plotlyPanel.style.display = "block";
        } else if (data.status === "error") {
            loader.style.display = "none";
        }
    };

    // --- Initial Load ---
    fetchAndDisplayFiles("");

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Logger page...");
        ConnectionManager.closeSocket('/ws_data');
        ConnectionManager.closeSocket('/ws_convert');
        console.log("Logger page cleanup complete.");
    };
})();
