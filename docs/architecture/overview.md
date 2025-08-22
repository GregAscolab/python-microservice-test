# Application Architecture Overview

This document outlines the high-level architecture of the Python microservice application. The system is designed to be modular, scalable, and resilient, with services communicating asynchronously via a central messaging broker.

## Core Components

-   **Microservices:** The application is broken down into small, independent services. Each service has a single responsibility (e.g., handling GPS data, managing settings, providing a UI).
-   **NATS Messaging Broker:** All communication between services happens via NATS. This decouples the services and allows for flexible data exchange patterns like publish-subscribe and request-reply.
-   **Manager Service:** The central orchestrator. It is responsible for discovering, starting, monitoring, and stopping all other microservices.
-   **UI Service:** The web-based frontend that allows users to interact with the application. It communicates with backend services via NATS over WebSockets.

## Architecture Diagram

The following diagram illustrates the relationship between the core components of the system.

```mermaid
graph TD
    subgraph "User Interaction"
        User[<font size=5>&#128100; User</font>]
    end

    subgraph "Application Services"
        Manager("Manager Service")
        Settings("Settings Service")
        GPS("GPS Service")
        CAN("CAN Bus Service")
        UI("UI Service")
        Other("...")
    end

    subgraph "Communication Bus"
        NATS[("NATS Broker")]
    end

    User -- HTTP/WebSocket --> UI

    UI <-->|Pub/Sub, Req/Rep| NATS
    Manager <-->|Pub/Sub, Req/Rep| NATS
    Settings <-->|Pub/Sub, Req/Rep| NATS
    GPS <-->|Pub/Sub, Req/Rep| NATS
    CAN <-->|Pub/Sub, Req/Rep| NATS
    Other <-->|Pub/Sub, Req/Rep| NATS

    Manager -- Spawns & Monitors --> Settings
    Manager -- Spawns & Monitors --> GPS
    Manager -- Spawns & Monitors --> CAN
    Manager -- Spawns & Monitors --> UI
    Manager -- Spawns & Monitors --> Other

    classDef service fill:#D6EAF8,stroke:#3498DB,stroke-width:2px;
    classDef nats fill:#F5B7B1,stroke:#C0392B,stroke-width:2px;
    classDef user fill:#D5F5E3,stroke:#2ECC71,stroke-width:2px;

    class User user;
    class Manager,Settings,GPS,CAN,UI,Other service;
    class NATS nats;
```

## Startup Sequence

The application is launched via the main `main.py` script, which only starts the **Manager Service**. The Manager then orchestrates the startup of all other services, ensuring the **Settings Service** is available before other services attempt to fetch their configuration.

The sequence diagram below details this process.

```mermaid
sequenceDiagram
    participant User
    participant TopLevelMain as "main.py"
    participant Manager as "Manager Service"
    participant Settings as "Settings Service"
    participant OtherServices as "Other Services (GPS, etc.)"
    participant NATS

    User->>+TopLevelMain: python main.py
    TopLevelMain->>+Manager: Starts Process
    Manager->>+NATS: Connect
    Manager->>+Settings: Spawns Process
    Settings->>+NATS: Connect
    Settings->>NATS: Subscribes to settings requests
    Manager->>Manager: Waits a moment for Settings to be ready
    loop For each other service
        Manager->>+OtherServices: Spawns Process
        OtherServices->>+NATS: Connect (temporary client)
        OtherServices->>NATS: Request "settings.get.all"
        NATS-->>OtherServices: Settings Response
        OtherServices->>NATS: Disconnect (temporary client)
        OtherServices->>+NATS: Connect (main client)
        OtherServices->>NATS: Subscribe to command subjects
        OtherServices->>NATS: Subscribe to data subjects
    end
    Manager-->>-TopLevelMain: Releases control (monitoring loop runs)
    TopLevelMain-->>-User: Logs output
```
