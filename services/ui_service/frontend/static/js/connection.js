class ConnectionManager {
    constructor() {
        this.sockets = {};
        this.connectionStatus = document.getElementById('connection-status');
        this.messageListeners = {};
    }

    connect(name, url) {
        this.sockets[name] = new WebSocket(url);

        this.sockets[name].onopen = () => {
            console.log(`${name} connection opened`);
            this.updateConnectionStatus('Connected', 'green');
        };

        this.sockets[name].onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (this.messageListeners[name]) {
                this.messageListeners[name].forEach(callback => callback(data));
            }
        };

        this.sockets[name].onerror = (error) => {
            console.error(`${name} error:`, error);
            this.updateConnectionStatus('Connection Error', 'red');
        };

        this.sockets[name].onclose = () => {
            console.log(`${name} connection closed`);
            this.updateConnectionStatus('Disconnected. Retrying...', 'orange');
            setTimeout(() => this.connect(name, url), 5000);
        };
    }

    updateConnectionStatus(text, color) {
        if (this.connectionStatus) {
            this.connectionStatus.textContent = text;
            this.connectionStatus.style.color = color;
        }
    }

    addMessageListener(socketName, callback) {
        if (!this.messageListeners[socketName]) {
            this.messageListeners[socketName] = [];
        }
        this.messageListeners[socketName].push(callback);
    }

    sendMessage(socketName, message) {
        if (this.sockets[socketName] && this.sockets[socketName].readyState === WebSocket.OPEN) {
            this.sockets[socketName].send(message);
        } else {
            console.error(`${socketName} socket not open`);
        }
    }
}

const connectionManager = new ConnectionManager();
connectionManager.connect('gps', "ws://" + window.location.host + "/ws_gps");
connectionManager.connect('data', "ws://" + window.location.host + "/ws_data");
connectionManager.connect('settings', "ws://" + window.location.host + "/ws_settings");
