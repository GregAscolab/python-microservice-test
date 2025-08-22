import { connect, JSONCodec, StringCodec, NatsError } from "/static/libs/nats-ws/nats.js";

const ConnectionManager = {
    _natsConnection: null,
    isOnline: false,
    appStatus: "unknown",
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    statusPollInterval: null,
    stringCodec: StringCodec(),
    jsonCodec: JSONCodec(),

    async getNatsConnection() {
        if (this._natsConnection && !this._natsConnection.isClosed()) {
            return this._natsConnection;
        }

        const connectToNats = async () => {
            try {
                const wsUrl = `ws://${window.location.hostname}:4223`;
                console.log(`Attempting to connect to NATS at ${wsUrl}...`);

                const nc = await connect({
                    servers: [wsUrl],
                    reconnect: true,
                    reconnectTimeWait: this.reconnectInterval,
                    maxReconnectAttempts: -1,
                });

                this._natsConnection = nc;
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

                this._natsConnection.closed().then((err) => {
                    console.log(`NATS connection closed: ${err}`);
                    this.isOnline = false;
                    this.appStatus = "offline";
                    this.updateGlobalStatus();
                    this._natsConnection = null;
                    setTimeout(connectToNats, this.reconnectInterval);
                });

                this.startStatusPolling();

            } catch (error) {
                console.error("Failed to connect to NATS:", error);
                this.isOnline = false;
                this.appStatus = "offline";
                this.updateGlobalStatus();
                this._natsConnection = null;
                setTimeout(connectToNats, this.reconnectInterval);
            }
        };

        await connectToNats();
        return this._natsConnection;
    },

    startStatusPolling() {
        if (this.statusPollInterval) {
            clearInterval(this.statusPollInterval);
        }
        this.statusPollInterval = setInterval(async () => {
            if (!this._natsConnection || this._natsConnection.isClosed()) {
                this.appStatus = "offline";
                this.updateGlobalStatus();
                return;
            }
            try {
                const res = await this._natsConnection.request("commands.manager", this.stringCodec.encode(JSON.stringify({command: "get_status"})));
                const status = this.jsonCodec.decode(res.data);
                this.appStatus = status.global_status;
            } catch (err) {
                if (err.code === "TIMEOUT") { // NatsError.REQ_TIMEOUT is not available in the browser
                    this.appStatus = "degraded";
                } else {
                    console.error("Error getting manager status:", err);
                    this.appStatus = "degraded";
                }
            }
            this.updateGlobalStatus();
        }, 10000);
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
        let status = "offline";
        if (this.isOnline) {
            if (this.appStatus === "all_ok") {
                status = "online";
            } else {
                status = "degraded";
            }
        }

        const event = new CustomEvent('connectionStatusChange', { detail: { status: status } });
        document.dispatchEvent(event);
        console.log(`Global connection status changed to: ${status}`);
    }
};

export default ConnectionManager;
