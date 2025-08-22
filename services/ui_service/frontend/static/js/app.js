import ConnectionManager from './connection_manager.js';

// --- Service Worker Registration ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js').then(registration => {
            console.log('ServiceWorker registration successful with scope: ', registration.scope);
        }, err => {
            console.log('ServiceWorker registration failed: ', err);
        });
    });
}

// --- Global Page State ---
let currentPage = {
    name: null,
    path: null
};

// --- Helper Functions ---
function getPageName(path) {
    // Converts '/can_bus_logger' -> 'CanBusLogger'
    // Converts '/app_logger' -> 'AppLogger'
    if (path.startsWith('/')) {
        path = path.substring(1);
    }
    if (path === "") {
        return "Dashboard";
    }
    return path.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('');
}

function showPage(path) {
    // 1. Run cleanup for the previous page if it exists
    if (currentPage.name) {
        const cleanupFunctionName = `cleanup${currentPage.name}Page`;
        if (typeof window[cleanupFunctionName] === 'function') {
            console.log(`Cleaning up page: ${currentPage.name}`);
            window[cleanupFunctionName]();
        }
    }

    // 2. Hide all page content divs
    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });

    // 3. Show the requested page content div
    const pageIdName = getPageName(path).toLowerCase();
    const pageDiv = document.getElementById(`page-${pageIdName}`);
    if (pageDiv) {
        pageDiv.style.display = 'flex';
    } else {
        // if the page is not found, default to the dashboard
        const dashboardPage = document.getElementById('page-dashboard');
        if (dashboardPage) {
            dashboardPage.style.display = 'flex';
        }
    }

    // 4. Call the init function for the new page
    const newPageName = getPageName(path);
    const initFunctionName = `init${newPageName}Page`;
    if (typeof window[initFunctionName] === 'function') {
        console.log(`Initializing page: ${newPageName}`);
        window[initFunctionName]();
    }

    // 5. Update global state
    currentPage.name = newPageName;
    currentPage.path = path;
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    // Initialize NATS connection
    ConnectionManager.getNatsConnection();

    // Handle navigation clicks
    document.querySelectorAll('.sidebar a').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const path = link.getAttribute('href');
            if (path === currentPage.path) return;

            history.pushState({path: path}, '', path);
            showPage(path);

            document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', event => {
        if (event.state && event.state.path) {
            const path = event.state.path;
            showPage(path);
            document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
            document.querySelector(`.sidebar a[href="${path}"]`).classList.add('active');
        }
    });

    // Initial page load
    const initialPath = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
    showPage(initialPath);
    document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
    const activeLink = document.querySelector(`.sidebar a[href="${initialPath}"]`);
    if(activeLink) activeLink.classList.add('active');
    history.replaceState({path: initialPath}, '', initialPath);
});

// Handle connection status changes
document.addEventListener('connectionStatusChange', event => {
    const statusDiv = document.getElementById('connection-status');
    if (event.detail.isOnline) {
        statusDiv.textContent = 'Online';
        statusDiv.classList.remove('status-offline');
        statusDiv.classList.add('status-online');
    } else {
        statusDiv.textContent = 'Offline';
        statusDiv.classList.remove('status-online');
        statusDiv.classList.add('status-offline');
    }
});
