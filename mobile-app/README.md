# Owasys Mobile Application

This directory contains the source code for the Owasys mobile application, built with React Native.

## Table of Contents

- [Owasys Mobile Application](#owasys-mobile-application)
  - [Table of Contents](#table-of-contents)
  - [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Configuration](#configuration)
    - [API Endpoint](#api-endpoint)
  - [Running the Application](#running-the-application)
    - [Starting the Backend](#starting-the-backend)
    - [Starting the Mobile App](#starting-the-mobile-app)
  - [Testing](#testing)
  - [Deployment](#deployment)
    - [Android](#android)
  - [Windows Development](#windows-development)

## Development Setup

### Prerequisites

- [Node.js](https://nodejs.org/) (v20 or later)
- [npm](https://www.npmjs.com/)
- [Java Development Kit (JDK)](https://www.oracle.com/java/technologies/downloads/) (version 11)
- [Android Studio](https://developer.android.com/studio) and the Android SDK

### Installation

1.  **Clone the repository** (if you haven't already).
2.  **Navigate to the project directory:**
    ```bash
    cd mobile-app/OwasysApp
    ```
3.  **Install the dependencies:**
    ```bash
    npm install
    ```

## Configuration

### API Endpoint

The mobile application connects to the backend API to fetch data. The base URL for the API is configured in `mobile-app/OwasysApp/src/config.ts`.

By default, the `API_URL` is set to `https://10.0.2.2:8443/api`, which is the standard address for accessing the host machine's localhost from an Android emulator. If you are running the backend on a different machine or need to use a different address, you can modify this file.

## Running the Application

### Starting the Backend

The mobile application requires the backend services to be running. Please refer to the main `README.md` file in the root of the repository for instructions on how to start the backend services.

### Starting the Mobile App

1.  **Start an Android emulator** from Android Studio or connect a physical device.
2.  **Run the application:**
    ```bash
    cd mobile-app/OwasysApp
    npm run android
    ```

## Testing

To run the test suite, use the following command:

```bash
cd mobile-app/OwasysApp
npm test
```

## Deployment

### Android

To build a release APK, follow these steps:

1.  **Generate a signing key.**
2.  **Configure Gradle to use the signing key.**
3.  **Build the release APK:**
    ```bash
    cd mobile-app/OwasysApp/android
    ./gradlew assembleRelease
    ```

## Windows Development

The development process on Windows is similar to macOS and Linux, but there are a few things to keep in mind:

-   **Use a modern terminal** like PowerShell or Windows Terminal.
-   **Ensure that your environment variables** (like `JAVA_HOME` and `ANDROID_HOME`) are set correctly.
-   **You may need to use `npx`** to run React Native commands if they are not in your system's PATH.
-   **When running the backend**, ensure that your firewall allows connections to the NATS server and the `ui_service`.
-   **For Android development**, the Android emulator can be more resource-intensive on Windows. Ensure you have sufficient RAM and have enabled hardware virtualization (VT-x) in your BIOS.