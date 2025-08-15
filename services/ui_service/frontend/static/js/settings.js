function initializeSettingsPage() {
    let settings = {};
    let activeTab = null;

    const handleSettingsMessage = (data) => {
        try {
            if (data.settings) {
                settings = data.settings;
                generateTabs(settings);
            } else {
                updateSettings(data);
            }
        } catch (error) {
            console.error("Error processing settings message:", error);
        }
    };

    const requestInitialSettings = () => {
        const message = {
            channel: 'settings',
            data: { command: 'get_all_settings' }
        };
        ConnectionManager.send(message);
    };

    ConnectionManager.register('settings', handleSettingsMessage);
    ConnectionManager.register('open', requestInitialSettings);

    if (ConnectionManager.connected) {
        requestInitialSettings();
    }

    function updateSettings(data) {
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;

            if (!settings[groupName]) {
                settings[groupName] = {};
            }
            if (!settings[groupName][settingName]) {
                settings[groupName][settingName] = {};
            }
            settings[groupName][settingName] = settingData.value;
        });
        generateTabs(settings);
    }

    function generateTabs(settings) {
        const tabButtonsContainer = $('.tab-buttons');
        const tabContentContainer = $('.tab-content');

        if (!tabButtonsContainer.length || !tabContentContainer.length) return;

        tabButtonsContainer.empty();
        tabContentContainer.empty();

        Object.keys(settings).forEach((groupName, index) => {
            const group = settings[groupName];
            const isActive = activeTab === groupName || (activeTab === null && index === 0);
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
                        channel: 'settings',
                        data: {
                            [settingName]: {
                                group: groupName,
                                value: newValue
                            }
                        }
                    };
                    ConnectionManager.send(updateData);
                });

                tabContent.append(inputField);
            });

            tabContentContainer.append(tabContent);

            tabButton.on('click', function() {
                $('.tab-button').removeClass('active');
                $('.tab-pane').removeClass('active');
                $(this).addClass('active');
                $(`#tab-${groupName}`).addClass('active');
                activeTab = groupName;
            });
        });
    }
}

if (typeof initializeSettingsPage === 'function') {
    initializeSettingsPage();
}
