# Communication and Messaging

Communication between microservices is exclusively handled by the NATS messaging system. This ensures that services are decoupled and can be developed, deployed, and scaled independently. This document defines the standard subject naming conventions and messaging patterns used throughout the application.

## Messaging Patterns

The application primarily uses two NATS messaging patterns:

-   **Publish/Subscribe:** Used for broadcasting data or events to any interested service. This is a one-to-many communication pattern.
    -   *Example:* The GPS service publishes location data to the `gps.data` subject, and both the UI service and an App Logger service might subscribe to it.
-   **Request/Reply:** Used when a service needs a direct response from another. This is a one-to-one communication pattern.
    -   *Example:* A service requests its configuration from the Settings Service by sending a message on `settings.get.all` and waiting for a response on a temporary, private reply subject.

## Subject Naming Conventions

A consistent naming convention for NATS subjects is crucial for maintaining clarity and avoiding collisions. The convention is as follows:

`<service_name>.<event_type>.<optional_subtype>`

-   **`<service_name>`:** The name of the service publishing the message (e.g., `gps`, `manager`, `ui`).
-   **`<event_type>`:** The type of event or data being published. Common types include:
    -   `status`: For publishing health or state information.
    -   `data`: For broadcasting primary data (e.g., `gps.data`).
    -   `log`: For logging messages.
-   **`<optional_subtype>`:** A more specific descriptor if needed (e.g., `log.error`).

### Command Subjects

To control services, a special `commands` subject is used. This is a critical pattern for service management.

**Format:** `commands.<service_name>`

-   Any service can send a command to another by publishing to this subject.
-   The payload is a JSON object specifying the command and its arguments:
    ```json
    {
      "command": "restart_service",
      "args": ["gps_service"]
    }
    ```
-   The `CommandHandler` class in `common/command_handler.py` is responsible for parsing these messages and dispatching them to the correct function within the service.

### Key Subjects

This table lists some of the most important subjects used in the application.

| Subject Pattern             | Description                                                  | Pattern         | Example Message/Payload                               |
| --------------------------- | ------------------------------------------------------------ | --------------- | ----------------------------------------------------- |
| `commands.<service_name>`   | Subject for sending commands to a specific service.          | Request/Reply   | `{"command": "get_status"}`                           |
| `manager.status`            | The Manager service publishes the status of all services here. | Publish/Subscribe | `{"global_status": "all_ok", "services": [...]}`      |
| `settings.get.all`          | Used by services to request their configuration.             | Request/Reply   | (Empty Payload)                                       |
| `<service_name>.data`       | Generic subject for a service to publish its primary data.   | Publish/Subscribe | `{"latitude": 45.123, "longitude": -75.456}` (from GPS) |
| `log.>`                     | Subject for publishing log messages from any service.        | Publish/Subscribe | `{"level": "INFO", "message": "Service started"}`     |
