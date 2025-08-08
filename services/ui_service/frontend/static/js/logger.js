// Logger JavaScript

function filterFiles() {
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

function formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

async function openFile(file, folder) {
    console.log(folder)

    document.getElementById("plotly-panel").style.display = "none";
    document.getElementById("loader").style.display = "block";
    const response = await fetch("/convert", {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type: "", name: file, folder:folder }),
    });
    console.log(JSON.stringify({ type: "", name: file, folder:folder }))
    const jsonData = await response.json();
    document.getElementById("loader").style.display = "none";
    displayPlot(jsonData);
    document.getElementById("plotly-panel").style.display = "block";
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
            idx:1
          };
        }

        const trace = {
          x: series.timestamps,
          y: series.values,
          type: 'scatter',
          mode: 'lines',
          name: series.name,
          yaxis: 'y'+plots[sig].idx,
        };
        plots[sig].idx++;

        plots[sig].traces.push(trace);
      });

      Object.keys(plots).forEach((sig) => {
        const plotDiv = document.createElement('div');
        // plotDiv.className = 'plotly-container';
        plotDiv.className = 'plotly-log-graph';
        plotsContainer.appendChild(plotDiv);

        const layout = {
          title: {
            text: plots[sig].title
          },
          autosize: true,
          // width:800,
          // height: 600,
          automargin: true,
          xaxis: {
            rangeslider: { visible: false },
            type: 'date',
            hovermode:'closest',
            showspikes : true,
            spikemode  : 'across',
            spikesnap : 'cursor',
            spikethickness:1,
            showline:true,
            showgrid:true,
          },
          yaxis: {
            fixedrange: false,
          },
          grid: {
            rows: plots[sig].traces.length,
            columns: 1,
            // pattern: 'independent',
            // roworder:'bottom to top'
          },
          showlegend : true,
          hovermode  : 'x'
        };

        const config = {responsive: true}

        Plotly.react(plotDiv, plots[sig].traces, layout, config);
      });
    }


    // Establish a WebSocket connection
const url = "ws://" + window.location.host + "/ws_data";
const socket = new WebSocket(url);

// Get the buttons
const toggleRecordingButton = document.getElementById('toggleRecording');
const recorderSpin = document.getElementById('recorderSpin');
const toggleRecordingCandumpButton = document.getElementById('toggleRecordingCandump');
const recorderCanDumpSpin = document.getElementById('recorderCanDumpSpin');
const toggleRecordingPythonCanButton = document.getElementById('toggleRecordingPythonCan');
const recorderPythonCanSpin = document.getElementById('recorderPythonCanSpin');
const quitButton = document.getElementById('quitButton');

// Variable to track recording state
let isRecording = false;
let isRecordingCandump = false;
let isRecordingPythonCan = false;

// Handle incoming messages
socket.onmessage = function(event) {
    // Parse the incoming message
    const data = JSON.parse(event.data);
    // console.log('WebSocket onmessage:', data);
};

// Handle WebSocket errors
socket.onerror = function(error) {
    console.error('WebSocket error:', error);
};

// Handle WebSocket close
socket.onclose = function(event) {
    console.log('WebSocket connection closed:', event);
};

// Toggle recording button click event
toggleRecordingButton.addEventListener('click', function() {
    isRecording = !isRecording;
    const command = isRecording ? 'startRecording' : 'stopRecording';
    socket.send(JSON.stringify({ command }));
    toggleRecordingButton.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
    recorderSpin.style.display = isRecording ? "block" : "none";
    toggleRecordingButton.classList.toggle('recording', isRecording);
});

// Toggle recording button click event
toggleRecordingCandumpButton.addEventListener('click', function() {
    isRecordingCandump = !isRecordingCandump;
    const command = isRecordingCandump ? 'startCanDumpRecording' : 'stopCanDumpRecording';
    socket.send(JSON.stringify({ command }));
    toggleRecordingCandumpButton.textContent = isRecordingCandump ? 'Stop Recording Candump' : 'Start Recording Candump';
    recorderCanDumpSpin.style.display = isRecordingCandump ? "block" : "none";
    toggleRecordingCandumpButton.classList.toggle('recording', isRecordingCandump);
});

// Toggle recording button click event
toggleRecordingPythonCanButton.addEventListener('click', function() {
    isRecordingPythonCan = !isRecordingPythonCan;
    const command = isRecordingPythonCan ? 'startPythonCanRecording' : 'stopPythonCanRecording';
    socket.send(JSON.stringify({ command }));
    toggleRecordingPythonCanButton.textContent = isRecordingPythonCan ? 'Stop Recording PythonCan' : 'Start Recording PythonCan';
    recorderPythonCanSpin.style.display = isRecordingPythonCan ? "block" : "none";
    toggleRecordingPythonCanButton.classList.toggle('recording', isRecordingPythonCan);
});

// Quit button click event
quitButton.addEventListener('click', function() {
    socket.send(JSON.stringify({ command: 'quit' }));
});
