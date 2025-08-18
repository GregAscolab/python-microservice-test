/**
 * connection.js
 *
 * This script provides a centralized manager for the WebSocket connection.
 * It handles establishing the connection, automatic reconnection with
 * exponential backoff, message dispatching, and keep-alive heartbeats.
 */
const ConnectionManager = {
    // --- Properties ---
    ws: null, // Holds the WebSocket object.
    url: `ws://${window.location.host}/ws`, // The URL for the single WebSocket endpoint.
    connected: false, // Flag to track connection status.
    reconnectInterval: 1000, // Initial reconnect interval in ms.
    maxReconnectInterval: 30000, // Maximum reconnect interval.
    messageHandlers: {}, // An object to store message handlers keyed by channel.

    /**
     * Initializes the ConnectionManager.
     */
    init: function() {
        this.connect();
        this.setupHeartbeat();
    },

    /**
     * Establishes the WebSocket connection.
     */
    connect: function() {
        // Prevent creating a new connection if one already exists or is in progress.
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.log("WebSocket is already connected or connecting.");
            return;
        }

        this.ws = new WebSocket(this.url);

        // --- WebSocket Event Handlers ---

        this.ws.onopen = () => {
            console.log("WebSocket connection established.");
            this.connected = true;
            this.updateStatus();
            this.reconnectInterval = 1000; // Reset interval on a successful connection.
            // Notify any registered 'open' handlers.
            if (this.messageHandlers['open']) {
                this.messageHandlers['open'].forEach(handler => handler());
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                // Dispatch the message to the appropriate handlers based on its channel.
                if (message.channel && this.messageHandlers[message.channel]) {
                    this.messageHandlers[message.channel].forEach(handler => handler(message.data));
                } else if (message.type === 'heartbeat' && message.status === 'alive') {
                    // Respond to server heartbeats to keep the connection alive.
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

    /**
     * Schedules a reconnect attempt with exponential backoff.
     */
    scheduleReconnect: function() {
        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval);
        // Increase the interval for the next attempt.
        this.reconnectInterval = Math.min(this.reconnectInterval * 2, this.maxReconnectInterval);
    },

    /**
     * Updates the connection status indicator in the UI.
     */
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

    /**
     * Registers a handler function for a specific message channel.
     * @param {string} channel - The channel to subscribe to.
     * @param {function} handler - The function to call when a message for this channel is received.
     */
    register: function(channel, handler) {
        if (!this.messageHandlers[channel]) {
            this.messageHandlers[channel] = [];
        }
        this.messageHandlers[channel].push(handler);
        console.log(`Handler registered for channel: ${channel}`);
    },

    /**
     * Sends data to the server via the WebSocket.
     * @param {object} data - The data to send (will be JSON.stringified).
     */
    send: function(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error("WebSocket is not connected. Cannot send message:", data);
        }
    },

    /**
     * Sets up a client-side heartbeat to keep the connection alive.
     */
    setupHeartbeat: function() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'heartbeat', status: 'ping' });
            }
        }, 20000); // Send a ping every 20 seconds.
    }
};

// Initialize the ConnectionManager when the DOM is ready.
document.addEventListener('DOMContentLoaded', () => {
    ConnectionManager.init();
});
