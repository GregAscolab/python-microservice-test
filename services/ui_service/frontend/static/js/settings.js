(function() {
    let settings = {};
    let activeTab = null;
    let isInitialized = false;
    let ws;

    function initSettingsPage() {
        if (isInitialized) {
            return;
        }
        console.log("Initializing Settings page...");
        isInitialized = true;
        // The rest of the initialization is driven by websocket messages
    }

    function onWsOpen() {
        console.log("Settings WebSocket opened.");
        initSettingsPage();
        // Maybe request settings on open? For now, we wait for the server to send them.
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

    // --- WebSocket Connection ---
    ws = ConnectionManager.getSocket('/ws_settings', onWsOpen, onWsMessage);

    // --- Helper functions ---
    function updateSettings(data) {
        console.log('Updating settings with data:', data);
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;

            if (settings[groupName] && settings[groupName][settingName] !== undefined) {
                settings[groupName][settingName] = settingData.value;
                // Update the input field if it's visible
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

        // Set the initial active tab if not already set
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
                            key: settingName, // Pass the key back
                            value: newValue
                        }
                    };
                    ws.send(JSON.stringify(updateData));
                });
                tabContent.append(inputField);
            });
            tabContentContainer.append(tabContent);

            tabButton.on('click', function() {
                activeTab = groupName; // Store the active tab name
                $('.tab-button').removeClass('active');
                $('.tab-pane').removeClass('active');
                $(this).addClass('active');
                $(`#tab-${groupName}`).addClass('active');
            });
        });
    }

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Settings page...");
        ConnectionManager.closeSocket('/ws_settings');
        isInitialized = false;
        activeTab = null;
        settings = {};
        console.log("Settings page cleanup complete.");
    };

})();
