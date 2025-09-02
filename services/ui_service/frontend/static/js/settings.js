import ConnectionManager from './connection_manager.js';

let activeTab = null;
let settings = {};
let tabButtonsContainer;
let tabContentContainer;
let settingsSub;

async function initSettingsPage() {
    console.log("Initializing Settings page...");

    tabButtonsContainer = document.querySelector('#page-settings .tab-buttons');
    tabContentContainer = document.querySelector('#page-settings .tab-content');

    if (!tabButtonsContainer || !tabContentContainer) return;

    tabButtonsContainer.addEventListener('click', onTabClick);

    // Get initial settings
    try {
        const response = await ConnectionManager.request('settings.get.all', '', 2000);
        const settings = ConnectionManager.jsonCodec.decode(response.data);
        if(settings) {
            generateTabs(settings);
        }
    } catch(err) {
        console.error("Failed to get settings:", err);
    }


    // Subscribe to updates
    ConnectionManager.subscribe('settings.updated', (m) => {
        const data = ConnectionManager.jsonCodec.decode(m.data);
        updateSettings(data);
    }).then(sub => {
        settingsSub = sub;
    });
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
    let newValue = input.value;

    // Attempt to parse as a number if it looks like one
    if (!isNaN(newValue) && newValue.trim() !== '') {
        newValue = parseFloat(newValue);
    }

    const command = {
        "command": "update_setting",
        "key": settingName,
        "value": newValue
    };

    ConnectionManager.publishJson('commands.settings_service', command);
}

function updateSettings(data) {
    Object.keys(data).forEach(settingName => {
        const settingData = data[settingName];
        if (settings[settingName] !== undefined) {
            settings[settingName] = settingData.value;
            const inputField = document.getElementById(settingName);
            if (inputField) {
                inputField.value = settingData.value;
            }
        }
    });
}

function loopInJson(group, groupName, tabContent, parent= null, level=1) {
    Object.keys(group).forEach(settingName => {
            const settingValue = group[settingName];

            if (typeof settingValue === 'object' && settingValue !== null) {
                console.log(settingName + " is an object: ", settingValue);
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'setting-group-field level-'+level;
                if (parent) {
                    fieldDiv.id = `${parent.id}.${settingName}`;
                }
                else {
                    fieldDiv.id = `${groupName}.${settingName}`;
                }

                const title = document.createElement('h'+level);
                title.textContent = settingName;

                fieldDiv.appendChild(title);
                if (parent) {
                    parent.appendChild(fieldDiv);
                }
                else{
                    tabContent.appendChild(fieldDiv);
                }

                return loopInJson(settingValue, groupName, tabContent, fieldDiv, level+1); // Recursive
            }
            else {
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'setting-field';

                const label = document.createElement('label');
                label.setAttribute('for', settingName);
                label.textContent = settingName;

                const input = document.createElement('input');
                input.type = 'text';
                if (parent) {
                    input.id = `${parent.id}.${settingName}`;
                }
                else {
                    input.id = `${groupName}.${settingName}`;
                }
                input.value = settingValue;
                input.addEventListener('change', onSettingChange);

                
                fieldDiv.appendChild(label);
                fieldDiv.appendChild(input);
                if (parent) {
                    parent.appendChild(fieldDiv);
                }
                else{
                    tabContent.appendChild(fieldDiv);
                }
            }
        });
};

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

        loopInJson(group, groupName, tabContent); // Recursive call !
        tabContentContainer.appendChild(tabContent);
    });
}

function cleanupSettingsPage() {
    console.log("Cleaning up Settings page...");
    if (settingsSub) {
        settingsSub.unsubscribe();
        settingsSub = null;
    }
    if (tabButtonsContainer) {
        tabButtonsContainer.removeEventListener('click', onTabClick);
    }
}

window.initSettingsPage = initSettingsPage;
window.cleanupSettingsPage = cleanupSettingsPage;
