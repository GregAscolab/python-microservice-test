// This script is loaded dynamically by app.js when the gps page is loaded
(function() {
    // --- Leaflet Map Initialization ---
    var map = L.map('map').setView([45.525, 4.924], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var marker = L.marker([45.525, 4.924]).addTo(map);

    // --- DataTable Initialization ---
    var gpsTable = $('#gpsDataTable').DataTable({
        "paging": false,
        "searching": false,
        "info": false,
        "order": []
    });

    // --- Plotly Skyview Initialization ---
    const skyviewDiv = document.getElementById('skyviewChart');
    const layout = {
        polar: {
            radialaxis: { tickfont: { size: 8 }, angle: 90, tickangle: 90, range: [90, 0] },
            angularaxis: { tickfont: { size: 10 }, rotation: 90, direction: "clockwise" }
        },
        showlegend: false,
        margin: { l: 40, r: 40, t: 40, b: 40 }
    };
    Plotly.newPlot(skyviewDiv, [], layout);

    // --- WebSocket Connection via ConnectionManager ---
    const ws_gps = ConnectionManager.getSocket('/ws_gps');

    ws_gps.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data && data.geometry && data.geometry.type === 'Point') {
            // Update Leaflet Map
            const coords = data.geometry.coordinates;
            const latLng = [coords[1], coords[0]];
            marker.setLatLng(latLng);
            map.setView(latLng, map.getZoom());

            // Update Data Table
            updateGpsTable(data.properties);

            // Update Skyview Chart
            if (data.properties && data.properties.SV) {
                updateSkyviewChart(data.properties.SV);
            }
        }
    };

    // --- Helper Functions ---
    function updateGpsTable(properties) {
        gpsTable.clear();
        const flattenObject = (obj, prefix = '') => {
            const result = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const newKey = prefix ? `${prefix}.${key}` : key;
                    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                        Object.assign(result, flattenObject(obj[key], newKey));
                    } else if (key !== 'SV') {
                        result[newKey] = obj[key];
                    }
                }
            }
            return result;
        };

        const flatProps = flattenObject(properties);
        for (const [key, value] of Object.entries(flatProps)) {
            let displayValue = value;
            if (typeof value === 'object' && value !== null && value.type === 'Buffer') {
                displayValue = String.fromCharCode.apply(null, value.data);
            } else if (Array.isArray(value)) {
                displayValue = JSON.stringify(value);
            }
            gpsTable.row.add([key, displayValue]);
        }
        gpsTable.draw();
    }

    function getSnrColor(snr) {
        if (snr >= 40) return 'green';
        if (snr >= 30) return 'yellow';
        if (snr > 0) return 'red';
        return 'grey';
    }

    function updateSkyviewChart(svData) {
        const satellites = svData.SV.filter(s => s.SV_Id > 0 && s.SV_Elevation > 0);
        const trace = {
            r: satellites.map(s => 90 - s.SV_Elevation),
            theta: satellites.map(s => s.SV_Azimuth),
            customdata: satellites.map(s => s.SV_SNR),
            mode: 'markers+text',
            text: satellites.map(s => s.SV_Id),
            textposition: 'top center',
            marker: {
                color: satellites.map(s => getSnrColor(s.SV_SNR)),
                size: 15,
                symbol: 'circle'
            },
            hovertemplate: "r=%{r} t=%{theta} snr=%{customdata}",
            type: 'scatterpolar'
        };
        Plotly.react(skyviewDiv, [trace], layout);
    }

    // --- Page Cleanup ---
    //currentPage is a global defined in app.js
    currentPage.cleanup = function() {
        console.log("Cleaning up GPS page...");
        // Close the WebSocket connection for this page
        ConnectionManager.closeSocket('/ws_gps');
        // Destroy the DataTable instance to prevent memory leaks
        if (gpsTable) {
            gpsTable.destroy();
        }
        // Clean up Plotly chart
        if (skyviewDiv) {
            Plotly.purge(skyviewDiv);
        }
        // Clean up Leaflet map
        if (map) {
            map.remove();
        }
        console.log("GPS page cleanup complete.");
    };
})();
