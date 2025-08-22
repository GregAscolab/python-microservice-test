import { connect, JSONCodec, StringCodec } from "/static/libs/nats-ws/nats.js";

const ConnectionManager = {
    _natsConnection: null,
    isOnline: false,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    stringCodec: StringCodec(),
    jsonCodec: JSONCodec(),

    async getNatsConnection() {
        if (this._natsConnection) {
            return this._natsConnection;
        }

        const connectToNats = async () => {
            try {
                const wsUrl = `ws://${window.location.hostname}:4223`;
                console.log(`Attempting to connect to NATS at ${wsUrl}...`);
                this._natsConnection = await connect({
                    servers: [wsUrl],
                    reconnect: true,
                    reconnectTimeWait: this.reconnectInterval,
                    maxReconnectAttempts: -1,
                });
                console.log(`Connected to NATS server ${this._natsConnection.getServer()}`);
                this.isOnline = true;
                this.updateGlobalStatus();

                (async () => {
                    for await (const status of this._natsConnection.status()) {
                        console.info(`NATS status: ${status.type}`);
                        this.isOnline = status.type === 'reconnect' || status.type === 'connect';
                        this.updateGlobalStatus();
                    }
                })().then();

                this._natsConnection.closed().then(() => {
                    console.log("NATS connection closed");
                    this.isOnline = false;
                    this.updateGlobalStatus();
                    this._natsConnection = null;
                    setTimeout(connectToNats, this.reconnectInterval);
                });

            } catch (error) {
                console.error("Failed to connect to NATS:", error);
                this.isOnline = false;
                this.updateGlobalStatus();
                this._natsConnection = null;
                setTimeout(connectToNats, this.reconnectInterval);
            }
        };

        await connectToNats();
        return this._natsConnection;
    },

    async subscribe(subject, callback) {
        const nc = await this.getNatsConnection();
        if (!nc) {
            console.error("Cannot subscribe, NATS connection not available");
            return null;
        }
        const sub = nc.subscribe(subject);
        (async () => {
            for await (const m of sub) {
                callback(m);
            }
        })();
        return sub;
    },

    async publish(subject, data) {
        const nc = await this.getNatsConnection();
        if (!nc) {
            console.error("Cannot publish, NATS connection not available");
            return;
        }
        nc.publish(subject, this.stringCodec.encode(data));
    },

    async publishJson(subject, data) {
        const nc = await this.getNatsConnection();
        if (!nc) {
            console.error("Cannot publish, NATS connection not available");
            return;
        }
        nc.publish(subject, this.jsonCodec.encode(data));
    },

    updateGlobalStatus: function() {
        const event = new CustomEvent('connectionStatusChange', { detail: { isOnline: this.isOnline } });
        document.dispatchEvent(event);
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.textContent = this.isOnline ? 'Online' : 'Offline';
            statusDiv.className = this.isOnline ? 'status-online' : 'status-offline';
        }
    }
};

export default ConnectionManager;
