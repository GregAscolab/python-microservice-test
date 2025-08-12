$(document).ready(function() {
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

    // --- Chart.js Skyview Initialization ---
    const skyviewCtx = document.getElementById('skyviewChart').getContext('2d');
    const skyviewChart = new Chart(skyviewCtx, {
        type: 'polarArea',
        data: {
            labels: [], // Satellite IDs will go here
            datasets: [{
                label: 'Satellites',
                data: [],
                backgroundColor: [],
                pointRadius: 7,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 90,
                    ticks: {
                        stepSize: 15
                    },
                    angleLines: {
                        display: true
                    },
                    pointLabels: {
                        display: true,
                        centerPointLabels: true,
                        font: {
                            size: 14
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const sat = context.raw;
                            return `ID: ${sat.id}, El: ${sat.elevation}°, Az: ${sat.azimuth}°, SNR: ${sat.snr}`;
                        }
                    }
                }
            }
        }
    });

    // --- WebSocket Connection ---
    const url_gps = "ws://" + window.location.host + "/ws_gps";
    const ws_gps = new WebSocket(url_gps);

    ws_gps.onopen = function(event) {
        console.log("GPS WebSocket connection opened.");
    };

    ws_gps.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Received GPS data:", data);

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

    ws_gps.onerror = function(error) {
        console.error('GPS WebSocket error:', error);
    };

    ws_gps.onclose = function(event) {
        console.log('GPS WebSocket connection closed:', event);
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
                    } else if (key !== 'SV') { // Exclude the large SV array from the table
                        result[newKey] = obj[key];
                    }
                }
            }
            return result;
        };

        const flatProps = flattenObject(properties);
        for (const [key, value] of Object.entries(flatProps)) {
            let displayValue = value;
            // Decode byte strings
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
        if (snr >= 40) return 'rgba(75, 192, 192, 0.8)';   // Green
        if (snr >= 30) return 'rgba(255, 206, 86, 0.8)';  // Yellow
        if (snr > 0) return 'rgba(255, 99, 132, 0.8)';    // Red
        return 'rgba(201, 203, 207, 0.5)';               // Grey for no signal
    }

    function updateSkyviewChart(svData) {
        const satellites = svData.SV.filter(s => s.SV_Id > 0 && s.SV_Elevation > 0);

        const chartData = satellites.map(sat => ({
            r: 90 - sat.SV_Elevation, // Invert elevation for polar chart (90 is center)
            t: sat.SV_Azimuth,
            id: sat.SV_Id,
            elevation: sat.SV_Elevation,
            azimuth: sat.SV_Azimuth,
            snr: sat.SV_SNR
        }));

        const backgroundColors = satellites.map(sat => getSnrColor(sat.SV_SNR));

        skyviewChart.data.datasets[0].data = chartData;
        skyviewChart.data.datasets[0].backgroundColor = backgroundColors;
        skyviewChart.update();
    }
});
