/**
 * settings.js
 *
 * This script manages the settings page. It dynamically generates tabs and input
 * fields based on configuration data received from the backend. It also handles
 * sending updated settings back to the server.
 */
function initializeSettingsPage() {
    let settings = {}; // Local cache for settings data.
    let activeTab = null; // Track the currently active tab.

    /**
     * Handles incoming messages from the 'settings' channel.
     * @param {object} data - The settings data or update from the server.
     */
    const handleSettingsMessage = (data) => {
        try {
            // If the message contains the full settings object, render everything.
            if (data.settings) {
                settings = data.settings;
                generateTabs(settings);
            } else {
                // Otherwise, it's an update to a single setting.
                updateSettings(data);
            }
        } catch (error) {
            console.error("Error processing settings message:", error);
        }
    };

    /**
     * Requests the initial full settings object from the server.
     */
    const requestInitialSettings = () => {
        const message = {
            channel: 'settings',
            data: { command: 'get_all_settings' }
        };
        ConnectionManager.send(message);
    };

    // Register WebSocket handlers.
    ConnectionManager.register('settings', handleSettingsMessage);
    ConnectionManager.register('open', requestInitialSettings);

    // If already connected, request settings immediately.
    if (ConnectionManager.connected) {
        requestInitialSettings();
    }

    /**
     * Updates the local settings cache with new data and re-renders the tabs.
     * @param {object} data - The settings update data.
     */
    function updateSettings(data) {
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;
            if (!settings[groupName]) settings[groupName] = {};
            if (!settings[groupName][settingName]) settings[groupName][settingName] = {};
            settings[groupName][settingName] = settingData.value;
        });
        generateTabs(settings); // Re-render to reflect the update.
    }

    /**
     * Generates the settings tabs and their content from the settings object.
     * @param {object} settingsData - The full settings object.
     */
    function generateTabs(settingsData) {
        const tabButtonsContainer = $('.tab-buttons');
        const tabContentContainer = $('.tab-content');
        if (!tabButtonsContainer.length || !tabContentContainer.length) return;

        // Clear existing tabs and content.
        tabButtonsContainer.empty();
        tabContentContainer.empty();

        // Create a tab for each group of settings.
        Object.keys(settingsData).forEach((groupName, index) => {
            const group = settingsData[groupName];
            const isActive = activeTab === groupName || (activeTab === null && index === 0);

            // Create the tab button.
            const tabButton = $(`<button class="tab-button ${isActive ? 'active' : ''}">${groupName}</button>`);
            tabButtonsContainer.append(tabButton);

            // Create the content pane for the tab.
            const tabContent = $(`<div class="tab-pane ${isActive ? 'active' : ''}" id="tab-${groupName}"></div>`);

            // Create input fields for each setting in the group.
            Object.keys(group).forEach(settingName => {
                const settingValue = group[settingName];
                const inputField = $(`
                    <div class="setting-field">
                        <label for="${settingName}">${settingName}</label>
                        <input type="text" id="${settingName}" value="${settingValue}">
                    </div>
                `);

                // Add an event listener to send updates to the server on change.
                inputField.find('input').on('change', function() {
                    const newValue = $(this).val();
                    const updateData = {
                        channel: 'settings',
                        data: {
                            [settingName]: { group: groupName, value: newValue }
                        }
                    };
                    ConnectionManager.send(updateData);
                });

                tabContent.append(inputField);
            });

            tabContentContainer.append(tabContent);

            // Add a click handler to switch between tabs.
            tabButton.on('click', function() {
                $('.tab-button').removeClass('active');
                $('.tab-pane').removeClass('active');
                $(this).addClass('active');
                $(`#tab-${groupName}`).addClass('active');
                activeTab = groupName; // Remember the active tab.
            });
        });
    }
}

// The initializeSettingsPage function will be called by app.js when the page is loaded.
