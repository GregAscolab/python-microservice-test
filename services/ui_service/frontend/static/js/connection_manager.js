const ConnectionManager = {
    _sockets: {},
    isOnline: false,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,

    getSocket: function(path) {
        const url = `ws://${window.location.host}${path}`;
        if (!this._sockets[url]) {
            this._sockets[url] = this.createSocket(url, path);
        }
        return this._sockets[url].publicInterface;
    },

    createSocket: function(url, path) {
        const socketWrapper = {
            instance: null,
            path: path,
            reconnectTimer: null,
            manualClose: false,
            attempts: 0,
            onMessageCallback: null,
            publicInterface: null,
            listeners: {} // Store listeners here
        };

        const publicInterface = {
            set onmessage(handler) {
                socketWrapper.onMessageCallback = handler;
                if (socketWrapper.instance) {
                    socketWrapper.instance.onmessage = handler;
                }
            },
            get onmessage() {
                return socketWrapper.onMessageCallback;
            },
            send: (data) => {
                if (socketWrapper.instance && socketWrapper.instance.readyState === WebSocket.OPEN) {
                    socketWrapper.instance.send(data);
                } else {
                    console.error(`WebSocket to ${url} not open. readyState: ${socketWrapper.instance?.readyState}. Cannot send data.`);
                }
            },
            close: () => {
                this.closeSocket(path);
            },
            get readyState() {
                return socketWrapper.instance ? socketWrapper.instance.readyState : WebSocket.CLOSED;
            },
            addEventListener: (type, listener) => {
                if (!socketWrapper.listeners[type]) {
                    socketWrapper.listeners[type] = [];
                }
                socketWrapper.listeners[type].push(listener);
                if (socketWrapper.instance) {
                    socketWrapper.instance.addEventListener(type, listener);
                }
            },
            removeEventListener: (type, listener) => {
                if (socketWrapper.listeners[type]) {
                    socketWrapper.listeners[type] = socketWrapper.listeners[type].filter(l => l !== listener);
                }
                if (socketWrapper.instance) {
                    socketWrapper.instance.removeEventListener(type, listener);
                }
            }
        };
        
        socketWrapper.publicInterface = publicInterface;

        const connect = () => {
            console.log(`Attempting to connect to ${url}...`);
            const ws = new WebSocket(url);
            socketWrapper.instance = ws;

            // Re-apply stored listeners from addEventListener
            for (const type in socketWrapper.listeners) {
                socketWrapper.listeners[type].forEach(listener => {
                    ws.addEventListener(type, listener);
                });
            }
            
            // Re-apply onmessage
            if (socketWrapper.onMessageCallback) {
                ws.onmessage = socketWrapper.onMessageCallback;
            }

            // Internal listeners for manager's own logic
            ws.addEventListener('open', () => {
                console.log(`WebSocket connected to ${url}`);
                socketWrapper.attempts = 0;
                this.reconnectInterval = 1000;
                this.updateGlobalStatus();
            });

            ws.addEventListener('close', (event) => {
                console.log(`WebSocket disconnected from ${url}. Code: ${event.code}`);
                if (!socketWrapper.manualClose) {
                    socketWrapper.attempts++;
                    const timeout = Math.min(this.maxReconnectInterval, this.reconnectInterval * Math.pow(2, socketWrapper.attempts));
                    console.log(`Will try to reconnect to ${url} in ${timeout} ms`);
                    socketWrapper.reconnectTimer = setTimeout(connect, timeout);
                }
                this.updateGlobalStatus();
            });

            ws.addEventListener('error', (error) => {
                console.error(`WebSocket error on ${url}:`, error);
            });
        };

        connect();
        return socketWrapper;
    },

    closeSocket: function(path) {
        const url = `ws://${window.location.host}${path}`;
        const socketWrapper = this._sockets[url];
        if (socketWrapper) {
            console.log(`Manually closing socket to ${url}`);
            socketWrapper.manualClose = true;
            if (socketWrapper.reconnectTimer) {
                clearTimeout(socketWrapper.reconnectTimer);
            }
            if (socketWrapper.instance) {
                socketWrapper.instance.close();
            }
            delete this._sockets[url];
            this.updateGlobalStatus();
        }
    },

    updateGlobalStatus: function() {
        let anySocketOpen = false;
        for (const url in this._sockets) {
            if (this._sockets[url].instance && this._sockets[url].instance.readyState === WebSocket.OPEN) {
                anySocketOpen = true;
                break;
            }
        }

        if (anySocketOpen !== this.isOnline) {
            this.isOnline = anySocketOpen;
            const event = new CustomEvent('connectionStatusChange', { detail: { isOnline: this.isOnline } });
            document.dispatchEvent(event);
            console.log(`Global connection status changed to: ${this.isOnline ? 'Online' : 'Offline'}`);
        }
    }
};
