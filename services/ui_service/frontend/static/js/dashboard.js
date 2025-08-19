(function() {
    // --- Initialize UI Components ---
    var map = L.map('map-dashboard').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var geoJSONLayer = L.geoJSON().addTo(map);

    var pressureTable = $('#pressureTable').DataTable({
        "paging": false,
        "searching": false,
        "info": false,
        "order": [],
        data:[],
        "createdRow": function(row, data, dataIndex) {
            $(row).attr('id', data[0]); // Set row id to the sensor name
        }
    });
    var angleTable = $('#angleTable').DataTable({
        "paging": false,
        "searching": false,
        "info": false,
        "order": [],
        data:[],
        "createdRow": function(row, data, dataIndex) {
            $(row).attr('id', data[0]); // Set row id to the sensor name
        }
    });

    // Period refresh of the display, based on value received and store in cache
    // const intervalID = setInterval(function() {
    //         angleTable.draw(false);
    //         pressureTable.draw(false);
    // }, 200);


    // --- WebSocket for GPS Data ---
    const ws_gps = ConnectionManager.getSocket('/ws_gps');
    ws_gps.onmessage = function(event) {
        var data = JSON.parse(event.data);
        if (data) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    };


    // --- WebSocket for Sensor Data ---
    const ws_data = ConnectionManager.getSocket('/ws_data');
    const nameCache = new Map(); // Cache to store received names/values

    const suffToTypeMap = new Map([
        ["_b", "pressure"],
        ["_PFAng", "angle"],
    ]);

    const typeToUnitMap = new Map([
        ["pressure", "bars"],
        ["angle", "deg"],
    ]);

    ws_data.onmessage = function(event) {
        const data = JSON.parse(event.data);

        // Check if the name already exists in the cache
        if (!nameCache.has(data.name)) {
            nameCache.set(data.name, data.value); // Add to cache first

            let unit = "";
            let targetTable;
            for (let [key, value] of suffToTypeMap) {
                if (data.name.includes(key)) {
                    targetTable = (value === 'pressure') ? pressureTable : angleTable;
                    unit = typeToUnitMap.get(value);
                    break;
                }
            }

            if (targetTable) {
                 targetTable.row.add([
                    data.name,
                    data.value,
                    unit
                ]).draw(false);
            }

        } else {
            // Update existing row
            nameCache.set(data.name, data.value);
            const row = $(`#${data.name}`);
            if (row.length) {
                // Find the correct table to update its data
                 let targetTable;
                 for (let [key, value] of suffToTypeMap) {
                    if (data.name.includes(key)) {
                        targetTable = (value === 'pressure') ? pressureTable : angleTable;
                        break;
                    }
                }
                if(targetTable) {
                    targetTable.cell(`#${data.name}`,1).data(data.value);
                }
            }
        }
    };

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Dashboard page...");
        // Close WebSocket connections
        ConnectionManager.closeSocket('/ws_gps');
        ConnectionManager.closeSocket('/ws_data');

        // Destroy DataTables
        if (pressureTable) pressureTable.destroy();
        if (angleTable) angleTable.destroy();

        // Clean up Leaflet map
        if (map) map.remove();
        console.log("Dashboard page cleanup complete.");
    };

})();
