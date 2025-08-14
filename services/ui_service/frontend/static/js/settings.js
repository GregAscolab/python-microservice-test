$(document).ready(function() {
    // Initialize settings
    let settings = {};
    let activeTab = null;

    // WebSocket connection
    const url = "ws://" + window.location.host + "/ws_settings";
    const ws = new WebSocket(url);

    // Handle WebSocket connection
    ws.onopen = function() {
        console.log("WebSocket connection established");
    };

    // Handle WebSocket messages
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("Received data:", data);

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

    // Handle WebSocket errors
    ws.onerror = function(error) {
        console.error("WebSocket error:", error);
    };

    // Handle WebSocket close
    ws.onclose = function() {
        console.log("WebSocket connection closed");
    };

    // Function to update settings
    function updateSettings(data) {
        console.log('UpdateSettings=' + JSON.stringify(data));
        Object.keys(data).forEach(settingName => {
            const settingData = data[settingName];
            const groupName = settingData.group;

            // Ensure the group exists
            if (!settings[groupName]) {
                settings[groupName] = {};
            }

            // Ensure the setting exists
            if (!settings[groupName][settingName]) {
                settings[groupName][settingName] = {};
            }

            // Update the setting
            settings[groupName][settingName] = settingData.value;
            // settings[groupName][settingName] = {
            //     value: settingData.value,
            //     unit: settingData.unit || settings[groupName][settingName].unit || "",
            //     ro: settingData.ro !== undefined ? settingData.ro : settings[groupName][settingName].ro || false
            // };
        });

        generateTabs(settings);
    }

    // Function to generate tabs and tab content
    function generateTabs(settings) {
        console.log('generateTabs');
        const tabButtonsContainer = $('.tab-buttons');
        const tabContentContainer = $('.tab-content');

        tabButtonsContainer.empty();
        tabContentContainer.empty();

        Object.keys(settings).forEach((groupName, index) => {
            const group = settings[groupName];

            // Determine if this tab should be active
            const isActive = activeTab === groupName || (activeTab === null && index === 0);

            // Generate tab button
            const tabButton = $(`<button class="tab-button ${isActive ? 'active' : ''}">${groupName}</button>`);
            tabButtonsContainer.append(tabButton);

            // Generate tab content
            const tabContent = $(`<div class="tab-pane ${isActive ? 'active' : ''}" id="tab-${groupName}"></div>`);

            // Generate input fields for each setting in the group
            Object.keys(group).forEach(settingName => {
                const setting = group[settingName];
                const inputField = $(`
                    <div class="setting-field">
                        <label for="${settingName}">${settingName}</label>
                        <input type="text" id="${settingName}" value="${setting}">
                        <!--
                        <input type="text" id="${settingName}" value="${setting.value}" ${setting.ro ? 'readonly' : ''}>
                        <span class="unit">${setting.unit}</span>
                        --!>
                    </div>
                `);

                // Add change event to input field
                inputField.find('input').on('change', function() {
                    const newValue = $(this).val();
                    const updateData = {
                        [settingName]: {
                            group: groupName,
                            value: newValue
                        }
                    };
                    ws.send(JSON.stringify(updateData));
                });

                tabContent.append(inputField);
            });

            tabContentContainer.append(tabContent);

            // Add click event to tab button
            tabButton.on('click', function() {
                $('.tab-button').removeClass('active');
                $('.tab-pane').removeClass('active');
                $(this).addClass('active');
                $(`#tab-${groupName}`).addClass('active');
                activeTab = groupName;
            });
        });
    }
});
