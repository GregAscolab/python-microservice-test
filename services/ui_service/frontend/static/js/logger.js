/**
 * logger.js
 *
 * This script provides the functionality for the logger page, which includes
 * viewing log files, starting/stopping recording, and converting log files for plotting.
 */
function initializeLoggerPage() {
    /**
     * Filters the list of files based on the selected extension.
     */
    window.filterFiles = function() {
        const filter = document.getElementById('extension-filter').value;
        const rows = document.querySelectorAll('.file-row');

        rows.forEach(row => {
            const ext = row.getAttribute('data-ext');
            const rowExt = ext.startsWith('.') ? ext.substring(1) : ext;
            if (filter === '' || rowExt === filter) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    /**
     * Formats a file size in bytes into a human-readable string.
     * @param {number} bytes - The file size in bytes.
     * @returns {string} The formatted file size.
     */
    window.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Initiates the conversion of a log file by sending a request to the backend.
     * @param {string} file - The name of the file to convert.
     * @param {string} folder - The folder where the file is located.
     * @param {HTMLElement} element - The table cell element that was clicked.
     */
    window.openFile = async function(file, folder, element) {
        // Reset UI elements.
        document.getElementById("plotly-panel").style.display = "none";
        document.getElementById("plotly-panel").innerHTML = '';
        document.querySelectorAll('.file-status').forEach(span => span.textContent = '');

        // Update status to "Queued".
        const statusSpan = element.parentElement.querySelector('.file-status');
        statusSpan.textContent = 'Queued...';
        document.getElementById("loader").style.display = "block";

        try {
            // Send the conversion request to the server.
            const response = await fetch("/convert", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: file, folder: folder }),
            });
            const result = await response.json();
            if (result.status !== "queued") {
                statusSpan.textContent = 'Error queueing';
                document.getElementById("loader").style.display = "none";
            }
        } catch (error) {
            console.error("Error calling /convert endpoint:", error);
            statusSpan.textContent = 'Error';
            document.getElementById("loader").style.display = "none";
        }
    }

    /**
     * Displays the converted log data in Plotly charts.
     * @param {Array} data - The array of data series to plot.
     */
    function displayPlot(data) {
        const plotsContainer = document.getElementById('plotly-panel');
        plotsContainer.innerHTML = '';
        const plots = {};

        // Group data series by signal type for plotting.
        data.forEach((series) => {
            let [prefix, part, sig] = series.name.split('_');
            if (!sig) sig = "Others";
            if (!plots[sig]) {
                plots[sig] = { traces: [], title: sig, idx: 1 };
            }
            const trace = {
                x: series.timestamps,
                y: series.values,
                type: 'scatter',
                mode: 'lines',
                name: series.name,
                yaxis: 'y' + plots[sig].idx,
            };
            plots[sig].idx++;
            plots[sig].traces.push(trace);
        });

        // Create a separate plot for each signal group.
        Object.keys(plots).forEach((sig) => {
            const plotDiv = document.createElement('div');
            plotDiv.className = 'plotly-log-graph';
            plotsContainer.appendChild(plotDiv);
            const layout = { /* Plotly layout configuration */ };
            Plotly.react(plotDiv, plots[sig].traces, layout, { responsive: true });
        });
    }

    // --- WebSocket Handlers ---
    const handleDataMessage = (data) => { /* Currently unused */ };

    /**
     * Handles messages about the file conversion process.
     * @param {object} data - The conversion status message.
     */
    const handleConvertMessage = (data) => {
        const filename = data.filename;
        const rows = document.querySelectorAll('.file-row');
        let targetRow = null;
        rows.forEach(row => {
            if (row.querySelector('td').textContent.trim() === filename) targetRow = row;
        });
        if (!targetRow) return;

        const statusSpan = targetRow.querySelector('.file-status');
        if (data.status === "started") {
            statusSpan.textContent = 'Converting...';
            document.getElementById("loader").style.display = "block";
            document.getElementById("plotly-panel").style.display = "none";
        } else if (data.status === "success") {
            statusSpan.textContent = 'Done';
            document.getElementById("loader").style.display = "none";
            displayPlot(data.data);
            document.getElementById("plotly-panel").style.display = "block";
        } else if (data.status === "error") {
            statusSpan.textContent = `Error: ${data.message}`;
            document.getElementById("loader").style.display = "none";
        }
    };

    ConnectionManager.register('can_data', handleDataMessage);
    ConnectionManager.register('conversion', handleConvertMessage);

    // --- Event Listeners ---
    const toggleRecordingButton = document.getElementById('toggleRecording');
    const recorderSpin = document.getElementById('recorderSpin');
    let isRecording = false;

    if (toggleRecordingButton) {
        toggleRecordingButton.addEventListener('click', function() {
            isRecording = !isRecording;
            const command = {
                channel: 'can_data',
                data: { command: isRecording ? 'startRecording' : 'stopRecording' }
            };
            ConnectionManager.send(command);
            toggleRecordingButton.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
            recorderSpin.style.display = isRecording ? "block" : "none";
            toggleRecordingButton.classList.toggle('recording', isRecording);

            if (!isRecording) {
                setTimeout(() => {
                    // Reload the logger content to see the new file.
                    window.dispatchEvent(new PopStateEvent('popstate', { state: { path: '/logger' } }));
                }, 1000);
            }
        });
    }
}

// The initializeLoggerPage function will be called by app.js when the page is loaded.
