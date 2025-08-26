# OWA Service

## Primary Responsibility

The OWA Service is responsible for managing the lifecycle of Owasys-specific hardware components. Its primary role is to initialize the hardware when the application starts and to gracefully shut it down when the application stops.

Other services that depend on this hardware, such as the `gps_service` when `hardware_platform` is set to `"owa5x"`, wait for this service to report a "ready" status before they attempt to access the hardware resources. This prevents race conditions and ensures an orderly startup.

**NOTE:** As of the current implementation, the hardware initialization logic within this service is commented out. The service's main effective function is to simply exist and publish its status, acting as a gatekeeper or a prerequisite for other hardware-dependent services.

## Subscriptions

| Subject                      | Description                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `owa.service.status.request` | Responds to direct requests for its current status (`initializing`, `ready`, `error`). |

## Publications

| Subject      | Description                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------- |
| `owa.status` | Publishes its final status (`ready` or `error`) after the startup logic completes for any service to see. |

## Workflow

The service's workflow is straightforward: it performs its startup, reports its status, and then waits to be shut down.

```mermaid
flowchart TD
    A[Start Service] --> B{Is `hardware_platform` == "owa5x"?};
    B -- No --> C[Set status to 'ready'];
    B -- Yes --> D["(Hardware initialization logic is currently commented out)"];
    D --> C;
    C --> E[Publish status to 'owa.status' subject];
    E --> F((Ready State));

    subgraph "On-Demand Status Check"
        G[Receive 'owa.service.status.request'] --> H[Reply to requestor with current status];
    end
```
