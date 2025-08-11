$(document).ready(function() {
    // Initialize Leaflet map
    var map = L.map('map').setView([45.525, 4.924], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var marker = L.marker([45.525, 4.924]).addTo(map);
    var geoJSONLayer = L.geoJSON().addTo(map);

    // Initialize DataTable
    var gpsTable = $('#gpsDataTable').DataTable({
        "paging": false,
        "searching": false,
        "info": false,
        "order": []
    });

    // WebSocket connection
    const url_gps = "ws://" + window.location.host + "/ws_gps";
    const ws_gps = new WebSocket(url_gps);

    ws_gps.onopen = function(event) {
        console.log("GPS WebSocket connection opened.");
    };

    ws_gps.onmessage = function(event) {
        var data = JSON.parse(event.data);
        console.log("Received GPS data:", data);

        if (data && data.geometry && data.geometry.type === 'Point') {
            // Update map
            var coords = data.geometry.coordinates;
            var latLng = [coords[1], coords[0]];
            marker.setLatLng(latLng);
            map.setView(latLng, map.getZoom());

            // Update table
            gpsTable.clear();
            if (data.properties) {
                for (const [key, value] of Object.entries(data.properties)) {
                    if (typeof value === 'object' && value !== null) {
                        for (const [subKey, subValue] of Object.entries(value)) {
                            gpsTable.row.add([`${key}.${subKey}`, JSON.stringify(subValue)]).draw();
                        }
                    } else {
                        gpsTable.row.add([key, value]).draw();
                    }
                }
            }
        }
    };

    ws_gps.onerror = function(error) {
        console.error('GPS WebSocket error:', error);
    };

    ws_gps.onclose = function(event) {
        console.log('GPS WebSocket connection closed:', event);
    };
});
