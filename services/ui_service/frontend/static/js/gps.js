// This script is loaded dynamically by app.js when the gps page is loaded
(function() {
    let map, gpsTable, skyviewDiv, marker, layout;
    let isInitialized = false;

    function initGpsPage() {
        if (isInitialized) {
            return;
        }
        console.log("Initializing GPS page...");

        map = L.map('map-gps').setView([45.525, 4.924], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        marker = L.marker([45.525, 4.924]).addTo(map);

        gpsTable = $('#gpsDataTable').DataTable({
            "paging": false, "searching": false, "info": false, "order": []
        });

        skyviewDiv = document.getElementById('skyviewChart');
        layout = {
            polar: {
                radialaxis: { tickfont: { size: 8 }, angle: 90, tickangle: 90, range: [90, 0] },
                angularaxis: { tickfont: { size: 10 }, rotation: 90, direction: "clockwise" }
            },
            showlegend: false, margin: { l: 40, r: 40, t: 40, b: 40 }
        };
        Plotly.newPlot(skyviewDiv, [], layout);

        isInitialized = true;
        console.log("GPS page initialization complete.");
    }

    function onWsMessage(event) {
        if (!isInitialized) return;
        const data = JSON.parse(event.data);
        if (data && data.geometry && data.geometry.type === 'Point') {
            const coords = data.geometry.coordinates;
            const latLng = [coords[1], coords[0]];
            marker.setLatLng(latLng);
            map.setView(latLng, map.getZoom());
            updateGpsTable(data.properties);
            if (data.properties && data.properties.SV) {
                updateSkyviewChart(data.properties.SV);
            }
        }
    }

    function onSocketReconnected(event, data) {
        if (data.path === '/ws_gps') {
            console.log("GPS page detected a reconnection for its socket. Data flow should resume.");
            // For a simple data stream like GPS, we might not need to do anything else.
            // If we needed to request initial data, we would do it here.
        }
    }

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
            marker: { color: satellites.map(s => getSnrColor(s.SV_SNR)), size: 15, symbol: 'circle' },
            hovertemplate: "r=%{r} t=%{theta} snr=%{customdata}",
            type: 'scatterpolar'
        };
        Plotly.react(skyviewDiv, [trace], layout);
    }

    // --- Main Execution ---
    initGpsPage();
    ConnectionManager.getSocket('/ws_gps', onWsMessage);
    $(document).on('socketReconnected.gps', onSocketReconnected);

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up GPS page...");
        ConnectionManager.closeSocket('/ws_gps');
        $(document).off('socketReconnected.gps');
        if (gpsTable) gpsTable.destroy();
        if (skyviewDiv) Plotly.purge(skyviewDiv);
        if (map) map.remove();
        isInitialized = false;
        console.log("GPS page cleanup complete.");
    };
})();
