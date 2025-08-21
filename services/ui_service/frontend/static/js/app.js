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

// Make currentPage globally accessible for page-specific scripts
let currentPage = {
    name: null,
    cleanup: function() {}
};

function getPageName(path) {
    return path.substring(1);
}

function loadScript(src) {
    return new Promise(function (resolve, reject) {
        // Check if script already exists
        if (document.querySelector(`script[src="${src}"]`)) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Script load error for ${src}`));
        document.head.appendChild(script);
    });
}

function showPage(path) {
    // 1. Run cleanup for the previous page
    if (typeof currentPage.cleanup === 'function') {
        console.log(`Cleaning up page: ${currentPage.name}`);
        currentPage.cleanup();
    }

    // 2. Hide all page content divs
    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });

    // 3. Show the requested page content div
    const pageName = getPageName(path);
    const pageDiv = document.getElementById(`page-${pageName}`);
    if (pageDiv) {
        pageDiv.style.display = 'flex';
    } else {
        document.getElementById('page-dashboard').style.display = 'flex'; // Default to dashboard
    }

    // 4. Load the corresponding script for the new page
    currentPage.name = pageName;
    currentPage.cleanup = function() {}; // Reset cleanup

    if (pageName) {
         loadScript(`/static/js/${pageName}.js`)
            .then(() => {
                console.log(`Script for ${pageName} loaded successfully.`);
            })
            .catch(error => {
                console.error(error);
            });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // --- Handle navigation clicks ---
    document.querySelectorAll('.sidebar a').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const path = link.getAttribute('href');
            if (path === window.location.pathname) return;

            history.pushState({path: path}, '', path);
            showPage(path);

            document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // --- Handle browser back/forward buttons ---
    window.addEventListener('popstate', event => {
        if (event.state && event.state.path) {
            const path = event.state.path;
            showPage(path);
            document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
            document.querySelector(`.sidebar a[href="${path}"]`).classList.add('active');
        }
    });

    // --- Initial page load ---
    const initialPath = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
    showPage(initialPath);
    document.querySelectorAll('.sidebar a').forEach(l => l.classList.remove('active'));
    document.querySelector(`.sidebar a[href="${initialPath}"]`).classList.add('active');
    history.replaceState({path: initialPath}, '', initialPath);
});

// --- UI handler for connection status ---
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
