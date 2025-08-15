function initializeLoggerPage() {
    // Logger JavaScript

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

    window.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    window.openFile = async function(file, folder, element) {
        // Clear previous results and hide the plot
        document.getElementById("plotly-panel").style.display = "none";
        document.getElementById("plotly-panel").innerHTML = '';

        // Reset all status indicators
        document.querySelectorAll('.file-status').forEach(span => span.textContent = '');

        // Set status to "Queued" for the clicked file
        const statusSpan = element.parentElement.querySelector('.file-status');
        statusSpan.textContent = 'Queued...';

        document.getElementById("loader").style.display = "block";

        try {
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

    function displayPlot(data) {
        const plotsContainer = document.getElementById('plotly-panel');
        plotsContainer.innerHTML = '';

        const plots = {};

        data.forEach((series) => {
            let [prefix, part, sig] = series.name.split('_');

            if (!sig) {
                sig = "Others";
            }

            if (!plots[sig]) {
                plots[sig] = {
                    traces: [],
                    title: sig,
                    idx: 1
                };
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

        Object.keys(plots).forEach((sig) => {
            const plotDiv = document.createElement('div');
            plotDiv.className = 'plotly-log-graph';
            plotsContainer.appendChild(plotDiv);

            const layout = {
                title: {
                    text: plots[sig].title
                },
                autosize: true,
                automargin: true,
                xaxis: {
                    rangeslider: { visible: false },
                    type: 'date',
                    hovermode: 'closest',
                    showspikes: true,
                    spikemode: 'across',
                    spikesnap: 'cursor',
                    spikethickness: 1,
                    showline: true,
                    showgrid: true,
                },
                yaxis: {
                    fixedrange: false,
                },
                grid: {
                    rows: plots[sig].traces.length,
                    columns: 1,
                },
                showlegend: true,
                hovermode: 'x'
            };

            const config = { responsive: true }

            Plotly.react(plotDiv, plots[sig].traces, layout, config);
        });
    }

    // --- WebSocket Handlers ---
    const handleDataMessage = (data) => {
        // console.log('WebSocket onmessage:', data);
    };

    const handleConvertMessage = (data) => {
        const filename = data.filename;
        const rows = document.querySelectorAll('.file-row');
        let targetRow = null;
        rows.forEach(row => {
            if (row.querySelector('td').textContent.trim() === filename) {
                targetRow = row;
            }
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
                    // Re-load content to refresh file list
                    window.dispatchEvent(new PopStateEvent('popstate', { state: { path: '/logger' } }));
                }, 1000);
            }
        });
    }
}

if (typeof initializeLoggerPage === 'function') {
    initializeLoggerPage();
}
