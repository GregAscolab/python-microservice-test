### How to run NATS Server with WebSocket support

1.  **Install Go**

    Follow the official instructions to install Go on your system: [https://golang.org/doc/install](https://golang.org/doc/install)

2.  **Install NATS Server**

    Once Go is installed, you can install the NATS server using the following command:
    ```bash
    go install github.com/nats-io/nats-server/v2@latest
    ```

3.  **Create a configuration file**

    Create a file named `nats-server.conf` with the following content:

    ```
    websocket {
        port: 4223
        no_tls: true
    }
    ```

4.  **Run the NATS server**

    Start the NATS server with the configuration file:

    ```bash
    nats-server -c nats-server.conf
    ```

    The NATS server will now be running with WebSocket support on port 4223.
