$(document).ready(function() {
    console.log("Attempting to connect to WebSocket...");

    const url_gps = "ws://" + window.location.host + "/ws_gps";
    const ws_gps = new WebSocket(url_gps);

    ws_gps.onopen = function(event) {
        console.log("GPS WebSocket connection successfully opened.");
    };

    ws_gps.onmessage = function(event) {
        console.log("Received GPS data:", event.data);
    };

    ws_gps.onerror = function(error) {
        console.error('GPS WebSocket error:', error);
    };

    ws_gps.onclose = function(event) {
        console.log('GPS WebSocket connection closed:', event);
    };
});
