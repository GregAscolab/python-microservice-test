// --- Settings Page ---
(function(window) {
    let ws;
    let activeTab = null;
    let settings = {};
    let tabButtonsContainer;
    let tabContentContainer;

    function initSettingsPage() {
        console.log("Initializing Settings page...");

        tabButtonsContainer = document.querySelector('#page-settings .tab-buttons');
        tabContentContainer = document.querySelector('#page-settings .tab-content');

        if (!tabButtonsContainer || !tabContentContainer) return;

        ws = ConnectionManager.getSocket('/ws_settings');
        ws.onmessage = onSocketMessage;

        tabButtonsContainer.addEventListener('click', onTabClick);
    }

    function onSocketMessage(event) {
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

    function onTabClick(e) {
        if (e.target.classList.contains('tab-button')) {
            const groupName = e.target.dataset.group;
            activeTab = groupName;

            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.style.display = 'none');

            e.target.classList.add('active');
            document.getElementById(`tab-${groupName}`).style.display = 'block';
        }
    }

    function onSettingChange(e) {
        const input = e.target;
        const settingName = input.id;
        const newValue = input.value;
        const groupName = input.closest('.tab-pane').id.replace('tab-', '');

        const updateData = {
            [settingName]: {
                group: groupName,
                key: settingName,
                value: newValue
            }
        };
        ws.send(JSON.stringify(updateData));
    }

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
        if (tabButtonsContainer) {
            tabButtonsContainer.removeEventListener('click', onTabClick);
        }
        // Input event listeners are attached to elements that get destroyed,
        // so we don't need to remove them manually.
    }

    window.initSettingsPage = initSettingsPage;
    window.cleanupSettingsPage = cleanupSettingsPage;

})(window);
