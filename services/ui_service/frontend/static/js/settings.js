// --- Settings Page ---
(function(window) {
    let ws;
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
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            if (settings[settingData.group] && settings[settingData.group][settingName] !== undefined) {
                settings[settingData.group][settingName] = settingData.value;
                const inputField = document.getElementById(settingName);
                if (inputField) {
                    inputField.value = settingData.value;
                }
            }
        });
    }

    function generateTabs(settingsData) {
        tabButtonsContainer.innerHTML = '';
        tabContentContainer.innerHTML = '';

        if (Object.keys(settingsData).length === 0) return;

        if (activeTab === null || !settingsData[activeTab]) {
            activeTab = Object.keys(settingsData)[0];
        }

        Object.keys(settingsData).forEach(groupName => {
            const group = settingsData[groupName];
            const isActive = activeTab === groupName;

            const tabButton = document.createElement('button');
            tabButton.className = 'tab-button';
            if(isActive) tabButton.classList.add('active');
            tabButton.textContent = groupName;
            tabButton.dataset.group = groupName;
            tabButtonsContainer.appendChild(tabButton);

            const tabContent = document.createElement('div');
            tabContent.className = 'tab-pane';
            if(isActive) tabContent.classList.add('active');
            tabContent.id = `tab-${groupName}`;
            tabContent.style.display = isActive ? 'block' : 'none';

            Object.keys(group).forEach(settingName => {
                const settingValue = group[settingName];
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'setting-field';

                const label = document.createElement('label');
                label.setAttribute('for', settingName);
                label.textContent = settingName;

                const input = document.createElement('input');
                input.type = 'text';
                input.id = settingName;
                input.value = settingValue;
                input.addEventListener('change', onSettingChange);

                fieldDiv.appendChild(label);
                fieldDiv.appendChild(input);
                tabContent.appendChild(fieldDiv);
            });
            tabContentContainer.appendChild(tabContent);
        });
    }

    function cleanupSettingsPage() {
        console.log("Cleaning up Settings page...");
        ConnectionManager.closeSocket('/ws_settings');
        isInitialized = false;
        activeTab = null;
        settings = {};
        console.log("Settings page cleanup complete.");
    };

})(window);
