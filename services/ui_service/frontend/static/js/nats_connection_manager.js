const NatsConnectionManager = {
    connection: null,
    isOnline: false,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    attempts: 0,
    subscriptions: {},

    async connect() {
        const servers = [{ servers: `ws://${window.location.hostname}:8080` }];
        try {
            this.connection = await nats.connect({ servers: servers });
            this.isOnline = true;
            this.attempts = 0;
            this.reconnectInterval = 1000;
            console.log('Connected to NATS server');
            this.updateGlobalStatus();
            this.resubscribe();

            (async () => {
                for await (const status of this.connection.status()) {
                    console.info(`NATS connection status changed to ${status.type}`);
                    this.isOnline = status.type === 'reconnect' || status.type === 'connect';
                    this.updateGlobalStatus();
                }
            })();

        } catch (err) {
            console.error('Failed to connect to NATS:', err);
            this.isOnline = false;
            this.updateGlobalStatus();
            this.scheduleReconnect();
        }
    },

    scheduleReconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        this.attempts++;
        const timeout = Math.min(this.maxReconnectInterval, this.reconnectInterval * Math.pow(2, this.attempts));
        console.log(`Will try to reconnect to NATS in ${timeout} ms`);
        this.reconnectTimer = setTimeout(() => this.connect(), timeout);
    },

    subscribe(subject, callback) {
        if (!this.subscriptions[subject]) {
            this.subscriptions[subject] = [];
        }
        this.subscriptions[subject].push(callback);

        if (this.connection) {
            const sub = this.connection.subscribe(subject);
            (async () => {
                for await (const m of sub) {
                    this.subscriptions[subject].forEach(cb => cb(m));
                }
            })();
        }
    },

    resubscribe() {
        for (const subject in this.subscriptions) {
            const sub = this.connection.subscribe(subject);
            (async () => {
                for await (const m of sub) {
                    this.subscriptions[subject].forEach(cb => cb(m));
                }
            })();
        }
    },

    updateGlobalStatus() {
        const event = new CustomEvent('connectionStatusChange', { detail: { isOnline: this.isOnline } });
        document.dispatchEvent(event);
        console.log(`Global connection status changed to: ${this.isOnline ? 'Online' : 'Offline'}`);
    },

    async close() {
        if (this.connection) {
            await this.connection.close();
            this.connection = null;
            this.isOnline = false;
            this.updateGlobalStatus();
            console.log('NATS connection closed');
        }
    }
};

// Initialize the connection
NatsConnectionManager.connect();
