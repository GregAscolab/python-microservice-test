const ConnectionManager = {
    // --- Properties ---
    ws: null,
    url: `ws://${window.location.host}/ws`,
    connected: false,
    reconnectInterval: 1000, // Start with 1 second
    maxReconnectInterval: 30000, // Cap at 30 seconds
    messageHandlers: {}, // Handlers for different message types, e.g., { 'gps': [handler1, handler2] }

    // --- Initialization ---
    init: function() {
        this.connect();
        this.setupHeartbeat();
    },

    // --- WebSocket Connection ---
    connect: function() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.log("WebSocket is already connected or connecting.");
            return;
        }

        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log("WebSocket connection established.");
            this.connected = true;
            this.updateStatus();
            this.reconnectInterval = 1000; // Reset reconnect interval on successful connection
            // If there's a handler for 'open', call it.
            if (this.messageHandlers['open']) {
                this.messageHandlers['open'].forEach(handler => handler());
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.channel && this.messageHandlers[message.channel]) {
                    this.messageHandlers[message.channel].forEach(handler => handler(message.data));
                } else if (message.type === 'heartbeat' && message.status === 'alive') {
                    // Respond to server's heartbeat to keep connection alive
                    this.send({ type: 'heartbeat', status: 'client_ack' });
                }
            } catch (e) {
                console.error("Failed to parse incoming message:", event.data, e);
            }
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            this.connected = false;
            this.updateStatus();
        };

        this.ws.onclose = () => {
            console.log("WebSocket connection closed. Attempting to reconnect...");
            this.connected = false;
            this.updateStatus();
            this.scheduleReconnect();
        };
    },

    // --- Reconnection Logic ---
    scheduleReconnect: function() {
        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval);

        // Exponential backoff
        this.reconnectInterval = Math.min(this.reconnectInterval * 2, this.maxReconnectInterval);
    },

    // --- UI and Status ---
    updateStatus: function() {
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            if (this.connected) {
                statusDiv.textContent = 'online';
                statusDiv.style.color = 'green';
            } else {
                statusDiv.textContent = 'offline';
                statusDiv.style.color = 'red';
            }
        }
    },

    // --- Message Handling ---
    register: function(channel, handler) {
        if (!this.messageHandlers[channel]) {
            this.messageHandlers[channel] = [];
        }
        this.messageHandlers[channel].push(handler);
        console.log(`Handler registered for channel: ${channel}`);
    },

    send: function(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error("WebSocket is not connected. Cannot send message:", data);
        }
    },

    // --- Keep-Alive ---
    setupHeartbeat: function() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                // Send a ping to the server to keep the connection alive
                this.send({ type: 'heartbeat', status: 'ping' });
            }
        }, 20000); // Send a ping every 20 seconds
    }
};

// Initialize the connection manager when the script loads
document.addEventListener('DOMContentLoaded', () => {
    ConnectionManager.init();
});
