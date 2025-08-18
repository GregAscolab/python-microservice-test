document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('toggleAppRecording');
    const recorderSpin = document.getElementById('recorderSpin');
    const loggerState = document.getElementById('logger-state');
    const startTime = document.getElementById('start-time');
    const startPosition = document.getElementById('start-position');
    const logContentPanel = document.getElementById('log-content-panel');
    const logContent = document.getElementById('log-content');

    let isRecording = false;

    const ws = new WebSocket(`ws://${window.location.host}/ws_app_logger`);

    ws.onopen = function(event) {
        console.log("WebSocket connection opened for app logger.");
    };

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Received data from app_logger.status:", data);

        isRecording = data.isRunning;
        updateUI();

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
            window.location.reload();
        }
    };

    ws.onclose = function(event) {
        console.log("WebSocket connection closed for app logger.");
    };

    ws.onerror = function(event) {
        console.error("WebSocket error:", event);
    };

    toggleButton.addEventListener('click', function() {
        const command = isRecording ? 'stop' : 'start';
        ws.send(JSON.stringify({ command: command }));
    });

    function updateUI() {
        if (isRecording) {
            toggleButton.textContent = 'Stop Recording';
            toggleButton.classList.add('recording');
            recorderSpin.style.display = 'block';
        } else {
            toggleButton.textContent = 'Start Recording';
            toggleButton.classList.remove('recording');
            recorderSpin.style.display = 'none';
        }
    }
});

function openAppLogFile(filename, element) {
    const logContentPanel = document.getElementById('log-content-panel');
    const logContent = document.getElementById('log-content');

    // Highlight the selected row
    const rows = document.querySelectorAll('#filenameTable tr');
    rows.forEach(row => row.classList.remove('selected'));
    element.parentElement.classList.add('selected');

    fetch(`/api/app_logs/${filename}`)
        .then(response => response.json())
        .then(data => {
            logContent.textContent = JSON.stringify(data, null, 2);
            logContentPanel.style.display = 'block';
        })
        .catch(error => {
            console.error('Error fetching log content:', error);
            logContent.textContent = 'Error loading log content.';
            logContentPanel.style.display = 'block';
        });
}
