# Python Microservice Application

This project is a Python-based microservice application designed for real-time data processing and user interaction, initially tailored for CAN bus data. The architecture is built around a set of communicating microservices that use a NATS broker for message passing.

## Project Overview

The core of the application is a set of independent microservices, each with a specific responsibility. This design allows for scalability, resilience, and easier development of new features.

- **Communication:** Services communicate via a [NATS](https://nats.io/) message broker.
- **Management:** A central manager service discovers, starts, and monitors all other services.
- **Configuration:** A dedicated settings service provides configuration to all other services.

## Directory Structure

The project is organized as follows:

```
/
├── services/
│   ├── manager/            # The microservice manager
│   ├── settings_service/   # Manages and provides settings
│   ├── can_bus_service/    # Handles CAN bus data (placeholder)
│   └── ui_service/         # User interface service (placeholder)
├── common/
│   └── microservice.py     # The abstract base class for all microservices
├── config/
│   └── settings.json       # Configuration file for all services
├── main.py                 # Main entry point to start the application
└── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Installation

1.  **Clone the repository** (or ensure all files are in place).
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up a NATS server.** The easiest way is to use Docker:
    ```bash
    docker run -p 4222:4222 -ti nats:latest
    ```
    The application is configured to connect to a NATS server at `nats://localhost:4222` by default.

## How to Run

To start the entire application, run the top-level `main.py` script:

```bash
python main.py
```

This will start the microservice manager, which will then discover and start all the other services, beginning with the settings service.

You should see output from the manager as it starts each service, followed by logs from the individual services themselves.

To stop the application, press `Ctrl+C` in the terminal where `main.py` is running. The manager will handle the graceful shutdown of all the services it started.

## Services Overview

-   **Manager Service (`services/manager`)**: The central nervous system of the application. It discovers and manages the lifecycle of all other services.
-   **Settings Service (`services/settings_service`)**: Loads configuration from `config/settings.json` and provides it to any service that requests it via NATS.
-   **CAN Bus Service (`services/can_bus_service`)**: A placeholder for the service that will interface with the CAN bus, decode data, and publish it to NATS.
-   **UI Service (`services/ui_service`)**: A placeholder for the service that will provide the user interface, likely using FastAPI and websockets.
