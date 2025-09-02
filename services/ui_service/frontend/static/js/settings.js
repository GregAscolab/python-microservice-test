import ConnectionManager from './connection_manager.js';

let activeTab = null;
let settings = {};
let tabButtonsContainer;
let tabContentContainer;
let settingsSub;
let reloadedSub;

// --- UI Elements ---
let exportBtn, importBtn, importFile, configSelect, loadConfigBtn;

async function initSettingsPage() {
    console.log("Initializing Settings page...");

    // Cache UI elements
    tabButtonsContainer = document.querySelector('#page-settings .tab-buttons');
    tabContentContainer = document.querySelector('#page-settings .tab-content');
    exportBtn = document.getElementById('export-settings-btn');
    importBtn = document.getElementById('import-settings-btn');
    importFile = document.getElementById('import-settings-file');
    configSelect = document.getElementById('config-files-select');
    loadConfigBtn = document.getElementById('load-config-file-btn');

    if (!tabButtonsContainer || !tabContentContainer) return;

    // Add event listeners
    tabButtonsContainer.addEventListener('click', onTabClick);
    exportBtn.addEventListener('click', onExportSettings);
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', onImportSettings);
    loadConfigBtn.addEventListener('click', onLoadConfigFile);

    // Fetch initial data
    await fetchAndRenderAllSettings();
    await populateConfigFiles();

    // Subscribe to updates
    ConnectionManager.subscribe('settings.updated', (m) => {
        const data = ConnectionManager.jsonCodec.decode(m.data);
        updateSettings(data);
    }).then(sub => {
        settingsSub = sub;
    });

    ConnectionManager.subscribe('settings.reloaded', async () => {
        console.log("Settings reloaded, refreshing UI...");
        await fetchAndRenderAllSettings();
        await populateConfigFiles();
    }).then(sub => {
        reloadedSub = sub;
    });
}

async function fetchAndRenderAllSettings() {
    try {
        const nc = await ConnectionManager.getNatsConnection();
        const response = await nc.request('settings.get.all', ConnectionManager.stringCodec.encode(''), { timeout: 2000 });
        const settingsData = ConnectionManager.jsonCodec.decode(response.data);
        settings = settingsData; // Store current settings
        if (settings) {
            generateTabs(settings);
        }
    } catch (err) {
        console.error("Failed to get settings:", err);
        tabContentContainer.innerHTML = `<p>Error loading settings. Please check the logs.</p>`;
    }
}

async function populateConfigFiles() {
    try {
        const nc = await ConnectionManager.getNatsConnection();
        const response = await nc.request('settings.list_configs', ConnectionManager.stringCodec.encode(''), { timeout: 2000 });
        const files = ConnectionManager.jsonCodec.decode(response.data);

        configSelect.innerHTML = ''; // Clear existing options
        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file;
            option.textContent = file;
            configSelect.appendChild(option);
        });
    } catch (err) {
        console.error("Failed to list config files:", err);
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

function loopInJson(group, groupName, tabContent, parent = null, level = 1) {
    Object.keys(group).forEach(settingName => {
        const settingValue = group[settingName];

        if (typeof settingValue === 'object' && settingValue !== null) {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'setting-group-field';
            // Add level class for styling hook
            fieldDiv.classList.add(`level-${level}`);

            if (parent) {
                fieldDiv.id = `${parent.id}.${settingName}`;
            } else {
                fieldDiv.id = `${groupName}.${settingName}`;
            }

            const title = document.createElement(`h${Math.min(level + 1, 6)}`); // Use h2, h3, etc.
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

function onExportSettings() {
    window.location.href = '/api/settings/export';
}

async function onImportSettings(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/settings/import', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            alert('Settings file imported successfully. The page will now reload.');
            // The settings.reloaded event will handle the UI refresh
        } else {
            const error = await response.json();
            alert(`Error importing file: ${error.message}`);
        }
    } catch (err) {
        console.error("Error uploading settings file:", err);
        alert('An unexpected error occurred during import.');
    } finally {
        // Reset file input
        importFile.value = '';
    }
}

function onLoadConfigFile() {
    const selectedFile = configSelect.value;
    if (!selectedFile) {
        alert("Please select a configuration file to load.");
        return;
    }

    const command = {
        command: "load_settings_from_file",
        filename: selectedFile
    };

    ConnectionManager.publishJson('commands.settings_service', command);
    alert(`Request to load '${selectedFile}' has been sent.`);
}

function cleanupSettingsPage() {
    console.log("Cleaning up Settings page...");
    if (settingsSub) {
        settingsSub.unsubscribe();
        settingsSub = null;
    }
    if (reloadedSub) {
        reloadedSub.unsubscribe();
        reloadedSub = null;
    }
    if (tabButtonsContainer) {
        tabButtonsContainer.removeEventListener('click', onTabClick);
    }
    if (exportBtn) exportBtn.removeEventListener('click', onExportSettings);
    if (importBtn) importBtn.removeEventListener('click', () => importFile.click());
    if (importFile) importFile.removeEventListener('change', onImportSettings);
    if (loadConfigBtn) loadConfigBtn.removeEventListener('click', onLoadConfigFile);
}

window.initSettingsPage = initSettingsPage;
window.cleanupSettingsPage = cleanupSettingsPage;
