const ConnectionManager = {
    sockets: {},
    isOnline: false,
    reconnectInterval: 1000, // Initial reconnect interval
    maxReconnectInterval: 30000, // Max reconnect interval

    getSocket: function(path, onOpenCallback, onMessageCallback) {
        const url = `ws://${window.location.host}${path}`;
        let socketWrapper = this.sockets[url];

        if (!socketWrapper) {
            socketWrapper = this.createSocket(url, path, onOpenCallback, onMessageCallback);
            this.sockets[url] = socketWrapper;
        } else {
            console.log(`Attaching new callbacks to existing socket for ${path}`);
            socketWrapper.onOpenCallback = onOpenCallback;
            socketWrapper.onMessageCallback = onMessageCallback;
            socketWrapper.instance.onmessage = socketWrapper.onMessageCallback;

            // If the socket is already open, we need to trigger the 'open' logic
            // for the new page that is taking it over.
            if (socketWrapper.instance && socketWrapper.instance.readyState === WebSocket.OPEN) {
                console.log(`Socket for ${path} is already open. Triggering onOpen callback manually.`);
                if (socketWrapper.onOpenCallback) {
                    socketWrapper.onOpenCallback();
                }
            }
        }
        return socketWrapper.instance;
    },

    createSocket: function(url, path, onOpenCallback, onMessageCallback) {
        const socketWrapper = {
            instance: null,
            path: path,
            reconnectTimer: null,
            manualClose: false,
            attempts: 0,
            onOpenCallback: onOpenCallback,
            onMessageCallback: onMessageCallback
        };

        const connect = () => {
            console.log(`Attempting to connect to ${url}...`);
            const ws = new WebSocket(url);
            socketWrapper.instance = ws;

            // Assign the onmessage handler
            ws.onmessage = socketWrapper.onMessageCallback;

            ws.addEventListener('open', () => {
                console.log(`WebSocket connected to ${url}`);
                socketWrapper.attempts = 0; // Reset reconnect attempts
                this.reconnectInterval = 1000; // Reset reconnect interval
                this.updateGlobalStatus();

                // Trigger the onOpen callback
                if (socketWrapper.onOpenCallback) {
                    socketWrapper.onOpenCallback();
                }
            });

            ws.addEventListener('close', (event) => {
                console.log(`WebSocket disconnected from ${url}. Code: ${event.code}`);
                if (!socketWrapper.manualClose) {
                    // Reconnect logic
                    socketWrapper.attempts++;
                    const timeout = Math.min(this.maxReconnectInterval, this.reconnectInterval * Math.pow(2, socketWrapper.attempts));
                    console.log(`Will try to reconnect to ${url} in ${timeout} ms`);
                    socketWrapper.reconnectTimer = setTimeout(connect, timeout);
                }
                this.updateGlobalStatus();
            });

            ws.addEventListener('error', (error) => {
                console.error(`WebSocket error on ${url}:`, error);
                // onclose will be called next, which will handle reconnection.
            });
        };

        connect(); // Initial connection attempt
        return socketWrapper;
    },

    closeSocket: function(path) {
        const url = `ws://${window.location.host}${path}`;
        const socketWrapper = this.sockets[url];
        if (socketWrapper) {
            console.log(`Manually closing socket to ${url}`);
            socketWrapper.manualClose = true;
            if (socketWrapper.reconnectTimer) {
                clearTimeout(socketWrapper.reconnectTimer);
            }
            if (socketWrapper.instance) {
                socketWrapper.instance.close();
            }
            delete this.sockets[url];
            this.updateGlobalStatus();
        }
    },

    updateGlobalStatus: function() {
        let anySocketOpen = false;
        for (const url in this.sockets) {
            if (this.sockets[url].instance && this.sockets[url].instance.readyState === WebSocket.OPEN) {
                anySocketOpen = true;
                break;
            }
        }

        if (anySocketOpen !== this.isOnline) {
            this.isOnline = anySocketOpen;
            // Trigger a custom event that the UI can listen to
            $(document).trigger('connectionStatusChange', { isOnline: this.isOnline });
            console.log(`Global connection status changed to: ${this.isOnline ? 'Online' : 'Offline'}`);
        }
    }
};
