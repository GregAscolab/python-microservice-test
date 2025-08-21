(function() {
    let map, geoJSONLayer, pressureTable, angleTable, intervalID;
    let isInitialized = false;
    const nameCache = new Map();

    const suffToTypeMap = new Map([["_b", "pressure"], ["_PFAng", "angle"]]);
    const typeToUnitMap = new Map([["pressure", "bars"], ["angle", "deg"]]);

    function initDashboardPage() {
        if (isInitialized) return;
        console.log("Initializing Dashboard page...");

        map = L.map('map-dashboard').setView([51.505, -0.09], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        geoJSONLayer = L.geoJSON().addTo(map);

        pressureTable = $('#pressureTable').DataTable({
            paging: false, searching: false, info: false, order: [], data: [],
            createdRow: function(row, data) { $(row).attr('id', data[0]); }
        });

        angleTable = $('#angleTable').DataTable({
            paging: false, searching: false, info: false, order: [], data: [],
            createdRow: function(row, data) { $(row).attr('id', data[0]); }
        });

        intervalID = setInterval(function() {
            nameCache.forEach(function(dataValue, dataName) {
                const cell = $(`#${dataName}_val`);
                cell.text(dataValue);
            });
        }, 200);

        isInitialized = true;
        console.log("Dashboard page initialization complete.");
    }

    function onWsGpsMessage(event) {
        if (!isInitialized) return;
        const data = JSON.parse(event.data);
        if (data && geoJSONLayer) {
            geoJSONLayer.clearLayers();
            geoJSONLayer.addData(data);
            map.fitBounds(geoJSONLayer.getBounds());
        }
    }

    function onWsDataMessage(event) {
        if (!isInitialized) return;
        const data = JSON.parse(event.data);
        if (!nameCache.has(data.name)) {
            nameCache.set(data.name, data.value);
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
                const rowNode = targetTable.row.add([data.name, data.value, unit]).draw(false).node();
                $(rowNode).find("td:eq(1)").attr('id', data.name + '_val');
            }
        } else {
            nameCache.set(data.name, data.value);
        }
    }

    function onSocketReconnected(event, data) {
        if (data.path === '/ws_gps' || data.path === '/ws_data') {
            console.log(`Dashboard detected a reconnection for socket: ${data.path}.`);
            // Data streams will just resume. If we needed to fetch initial state, we'd do it here.
        }
    }

    // --- Main Execution ---
    initDashboardPage();
    ConnectionManager.getSocket('/ws_gps', onWsGpsMessage);
    ConnectionManager.getSocket('/ws_data', onWsDataMessage);
    $(document).on('socketReconnected.dashboard', onSocketReconnected);

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Dashboard page...");
        if (intervalID) clearInterval(intervalID);
        ConnectionManager.closeSocket('/ws_gps');
        ConnectionManager.closeSocket('/ws_data');
        $(document).off('socketReconnected.dashboard');

        if (pressureTable) pressureTable.destroy();
        if (angleTable) angleTable.destroy();
        if (map) map.remove();

        isInitialized = false;
        nameCache.clear();
        console.log("Dashboard page cleanup complete.");
    };
})();
