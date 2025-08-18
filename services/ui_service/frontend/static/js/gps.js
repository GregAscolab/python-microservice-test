/**
 * gps.js
 *
 * This script manages the functionality of the GPS page.
 * It initializes the map, data table, and skyview chart, and it
 * handles incoming GPS data from the WebSocket to update the UI.
 */
function initializeGpsPage() {
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
            radialaxis: {
                tickfont: { size: 8 },
                angle: 90,
                tickangle: 90,
                range: [90, 0]
            },
            angularaxis: {
                tickfont: { size: 10 },
                rotation: 90,
                direction: "clockwise"
            }
        },
        showlegend: false,
        margin: { l: 40, r: 40, t: 40, b: 40 }
    };
    Plotly.newPlot(skyviewDiv, [], layout);

    /**
     * Handles incoming GPS data from the WebSocket.
     * @param {object} data - The GPS data received from the server.
     */
    const handleGpsMessage = (data) => {
        if (data && data.geometry && data.geometry.type === 'Point') {
            // Update the Leaflet map with the new coordinates.
            const coords = data.geometry.coordinates;
            const latLng = [coords[1], coords[0]];
            marker.setLatLng(latLng);
            map.setView(latLng, map.getZoom());

            // Update the data table with GPS properties.
            updateGpsTable(data.properties);

            // Update the skyview chart with satellite data.
            if (data.properties && data.properties.SV) {
                updateSkyviewChart(data.properties.SV);
            }
        }
    };

    // Register the GPS message handler with the central ConnectionManager.
    ConnectionManager.register('gps', handleGpsMessage);

    /**
     * Updates the GPS data table with new properties.
     * @param {object} properties - The properties object from the GPS data.
     */
    function updateGpsTable(properties) {
        gpsTable.clear();
        // Flatten the nested properties object for display.
        const flattenObject = (obj, prefix = '') => {
            const result = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const newKey = prefix ? `${prefix}.${key}` : key;
                    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                        Object.assign(result, flattenObject(obj[key], newKey));
                    } else if (key !== 'SV') { // Exclude the raw satellite vehicle data from the table.
                        result[newKey] = obj[key];
                    }
                }
            }
            return result;
        };

        const flatProps = flattenObject(properties);
        for (const [key, value] of Object.entries(flatProps)) {
            let displayValue = value;
            // Handle special data types for display.
            if (typeof value === 'object' && value !== null && value.type === 'Buffer') {
                displayValue = String.fromCharCode.apply(null, value.data);
            } else if (Array.isArray(value)) {
                displayValue = JSON.stringify(value);
            }
            gpsTable.row.add([key, displayValue]);
        }
        gpsTable.draw();
    }

    /**
     * Determines the color for a satellite based on its signal-to-noise ratio (SNR).
     * @param {number} snr - The SNR value.
     * @returns {string} The color name.
     */
    function getSnrColor(snr) {
        if (snr >= 40) return 'green';
        if (snr >= 30) return 'yellow';
        if (snr > 0) return 'red';
        return 'grey';
    }

    /**
     * Updates the skyview chart with satellite data.
     * @param {object} svData - The satellite vehicle data.
     */
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
}

// Since app.js loads this script dynamically, this ensures the initialization function is called.
if (typeof initializeGpsPage === 'function') {
    initializeGpsPage();
}
