/**
 * layout_manager.js
 *
 * This module is responsible for managing the collapsible side panels
 * across the entire application. It centralizes the logic for toggling
 * panel visibility and handling responsive layout changes.
 */

const panelStates = {}; // Stores the state of each panel (e.g., { 'panel-id': { isCollapsed: false } })

/**
 * Initializes the layout manager.
 * Finds all toggle buttons and their corresponding panels,
 * sets up initial states, and attaches event listeners.
 */
function initLayoutManager() {
    console.log("Initializing Layout Manager...");

    const toggleButtons = document.querySelectorAll('.btn-toggle-panel-left, .btn-toggle-panel-right');

    toggleButtons.forEach(button => {
        const panelId = button.dataset.panelId;
        if (!panelId) {
            console.warn("Found a toggle button without a 'data-panel-id' attribute:", button);
            return;
        }

        const panel = document.getElementById(panelId);
        if (!panel) {
            console.warn(`Could not find panel with ID: ${panelId}`);
            return;
        }

        // Initialize state for each panel
        panelStates[panelId] = {
            isCollapsed: false,
            button: button,
            panel: panel
        };

        // Attach click listener to the button
        button.addEventListener('click', () => {
            togglePanel(panelId);
        });
    });

    // Add a single listener for window resize events
    window.addEventListener('resize', updateAllLayouts);

    // Initial layout update
    updateAllLayouts();
}

/**
 * Toggles the collapsed/open state of a specific panel.
 * @param {string} panelId - The ID of the panel to toggle.
 */
function togglePanel(panelId) {
    if (panelStates[panelId]) {
        panelStates[panelId].isCollapsed = !panelStates[panelId].isCollapsed;
        updateLayout(panelId);

        // After the CSS transition (300ms), dispatch a resize event
        // to make Plotly graphs resize themselves to the new container width.
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 350);
    }
}

/**
 * Updates the layout for a single panel based on its state and window width.
 * @param {string} panelId - The ID of the panel to update.
 */
function updateLayout(panelId) {
    const state = panelStates[panelId];
    if (!state) return;

    const isNarrow = window.innerWidth <= 1200;

    // Remove all state classes first
    state.panel.classList.remove('open', 'collapsed');

    if (state.isCollapsed) {
        if (isNarrow) {
            // On narrow screens, a collapsed panel is just not open
            state.panel.classList.remove('open');
        } else {
            // On wide screens, add 'collapsed'
            state.panel.classList.add('collapsed');
        }
    } else {
         if (isNarrow) {
            // On narrow screens, an un-collapsed panel is 'open'
            state.panel.classList.add('open');
        } else {
            // On wide screens, an un-collapsed panel has no extra class
            state.panel.classList.remove('collapsed');
        }
    }
}

/**
 * A function that is called on window resize to update all panels.
 */
function updateAllLayouts() {
    for (const panelId in panelStates) {
        updateLayout(panelId);
    }
}

// Export the init function so it can be called from app.js
export { initLayoutManager };