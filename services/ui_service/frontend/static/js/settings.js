(function() {
    let settings = {};
    let activeTab = null;
    let isInitialized = false;
    let ws;

    function initSettingsPage() {
        if (isInitialized) return;
        console.log("Initializing Settings page...");
        // Request initial settings from server
        sendCommand({ command: 'get_settings' });
        isInitialized = true;
    }

    function sendCommand(data) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
        } else {
            console.error("Settings WebSocket is not open. Cannot send command.");
        }
    }

    function onWsMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("Received settings data:", data);

            if (data.settings) {
                settings = data.settings;
                generateTabs(settings);
            } else {
                updateSettings(data);
            }
        } catch (error) {
            console.error("Error parsing WebSocket message:", error);
        }
    }

    function onSocketReconnected(event, data) {
        if (data.path === '/ws_settings') {
            console.log("Settings page detected a reconnection. Re-fetching settings.");
            sendCommand({ command: 'get_settings' });
        }
    }

    function updateSettings(data) {
        console.log('Updating settings with data:', data);
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;

            if (settings[groupName] && settings[groupName][settingName] !== undefined) {
                settings[groupName][settingName] = settingData.value;
                const inputField = $(`#${settingName}`);
                if (inputField.length) {
                    inputField.val(settingData.value);
                }
            }
        });
    }

    function generateTabs(settingsData) {
        const tabButtonsContainer = $('.tab-buttons');
        const tabContentContainer = $('.tab-content');
        tabButtonsContainer.empty();
        tabContentContainer.empty();

        if (Object.keys(settingsData).length === 0) return;

        if (activeTab === null || !settingsData[activeTab]) {
            activeTab = Object.keys(settingsData)[0];
        }

        Object.keys(settingsData).forEach(groupName => {
            const group = settingsData[groupName];
            const isActive = activeTab === groupName;

            const tabButton = $(`<button class="tab-button ${isActive ? 'active' : ''}">${groupName}</button>`);
            tabButtonsContainer.append(tabButton);

            const tabContent = $(`<div class="tab-pane ${isActive ? 'active' : ''}" id="tab-${groupName}"></div>`);

            Object.keys(group).forEach(settingName => {
                const settingValue = group[settingName];
                const inputField = $(`
                    <div class="setting-field">
                        <label for="${settingName}">${settingName}</label>
                        <input type="text" id="${settingName}" value="${settingValue}">
                    </div>
                `);

                inputField.find('input').on('change', function() {
                    const newValue = $(this).val();
                    const updateData = {
                        [settingName]: {
                            group: groupName,
                            key: settingName,
                            value: newValue
                        }
                    };
                    sendCommand(updateData);
                });
                tabContent.append(inputField);
            });
            tabContentContainer.append(tabContent);

            tabButton.on('click', function() {
                activeTab = groupName;
                $('.tab-button').removeClass('active');
                $('.tab-pane').removeClass('active');
                $(this).addClass('active');
                $(`#tab-${groupName}`).addClass('active');
            });
        });
    }

    // --- Main Execution ---
    initSettingsPage();
    ws = ConnectionManager.getSocket('/ws_settings', onWsMessage);
    $(document).on('socketReconnected.settings', onSocketReconnected);

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Settings page...");
        ConnectionManager.closeSocket('/ws_settings');
        $(document).off('socketReconnected.settings');
        isInitialized = false;
        activeTab = null;
        settings = {};
        console.log("Settings page cleanup complete.");
    };
})();
