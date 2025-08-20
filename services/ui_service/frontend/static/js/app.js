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

$(document).ready(function() {

    function getPageName(path) {
        return path.substring(1);
    }

    function showPage(path) {
        // 1. Run cleanup for the previous page
        if (typeof currentPage.cleanup === 'function') {
            console.log(`Cleaning up page: ${currentPage.name}`);
            currentPage.cleanup();
        }

        // 2. Hide all page content divs
        $('.page-content').hide();

        // 3. Show the requested page content div
        const pageName = getPageName(path);
        const $page = $(`#page-${pageName}`);
        if ($page.length) {
            $page.css( "display", "flex" );
        } else {
            // If page not found, maybe show a default or a 404 div
            $('#page-dashboard').css( "display", "flex" ); // Default to dashboard
        }

        // 4. Load the corresponding script for the new page
        currentPage.name = pageName;
        currentPage.cleanup = function() {}; // Reset cleanup

        if (pageName) {
             $.getScript(`/static/js/${pageName}.js`)
                .done(function(script, textStatus) {
                    console.log(`Script for ${pageName} loaded successfully.`);
                })
                .fail(function(jqxhr, settings, exception) {
                    console.error(`Error loading script for ${pageName}:`, exception);
                });
        }
    }

    // --- Handle navigation clicks ---
    $('.sidebar a').on('click', function(e) {
        e.preventDefault();
        const path = $(this).attr('href');
        if (path === window.location.pathname) return;

        history.pushState({path: path}, '', path);
        showPage(path);
        $('.sidebar a').removeClass('active');
        $(this).addClass('active');
    });

    // --- Handle browser back/forward buttons ---
    window.onpopstate = function(event) {
        if (event.state && event.state.path) {
            const path = event.state.path;
            showPage(path);
            $('.sidebar a').removeClass('active');
            $(`.sidebar a[href="${path}"]`).addClass('active');
        }
    };

    // --- Initial page load ---
    const initialPath = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
    showPage(initialPath);
    $('.sidebar a').removeClass('active');
    $(`.sidebar a[href="${initialPath}"]`).addClass('active');
    history.replaceState({path: initialPath}, '', initialPath);
});
