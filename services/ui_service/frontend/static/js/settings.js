(function() {
    let settings = {};
    let activeTab = null;

    const tabButtonsContainer = document.querySelector('#page-settings .tab-buttons');
    const tabContentContainer = document.querySelector('#page-settings .tab-content');

    // --- WebSocket Connection ---
    const ws = ConnectionManager.getSocket('/ws_settings');

    // --- Handle WebSocket messages ---
    ws.onmessage = function(event) {
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
    };

    // --- Helper functions ---
    function updateSettings(data) {
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;

            if (settings[groupName] && settings[groupName][settingName] !== undefined) {
                settings[groupName][settingName] = settingData.value;
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
            tabButton.className = `tab-button ${isActive ? 'active' : ''}`;
            tabButton.textContent = groupName;
            tabButton.dataset.group = groupName;
            tabButtonsContainer.appendChild(tabButton);

            const tabContent = document.createElement('div');
            tabContent.className = `tab-pane ${isActive ? 'active' : ''}`;
            tabContent.id = `tab-${groupName}`;

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

                input.addEventListener('change', () => {
                    const newValue = input.value;
                    const updateData = {
                        [settingName]: {
                            group: groupName,
                            key: settingName,
                            value: newValue
                        }
                    };
                    ws.send(JSON.stringify(updateData));
                });

                fieldDiv.appendChild(label);
                fieldDiv.appendChild(input);
                tabContent.appendChild(fieldDiv);
            });
            tabContentContainer.appendChild(tabContent);
        });
    }

    // --- Event Delegation for Tab Clicks ---
    tabButtonsContainer.addEventListener('click', e => {
        if (e.target.classList.contains('tab-button')) {
            const groupName = e.target.dataset.group;
            activeTab = groupName;

            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            e.target.classList.add('active');
            document.getElementById(`tab-${groupName}`).classList.add('active');
        }
    });

    // --- Page Cleanup ---
    currentPage.cleanup = function() {
        console.log("Cleaning up Settings page...");
        ConnectionManager.closeSocket('/ws_settings');
        console.log("Settings page cleanup complete.");
    };

})();
