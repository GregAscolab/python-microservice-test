$(document).ready(function() {
    const $mainContent = $('#content');
    // Keep track of the current page's specific logic and cleanup function
    let currentPage = {
        name: null,
        cleanup: function() {}
    };

    function getPageName(path) {
        // Extracts 'gps' from '/gps'
        return path.substring(1);
    }

    // --- Helper function to load content and scripts ---
    function loadPage(path) {
        // 1. Run cleanup for the previous page
        if (typeof currentPage.cleanup === 'function') {
            console.log(`Cleaning up page: ${currentPage.name}`);
            currentPage.cleanup();
        }
        $mainContent.empty(); // Clear content immediately

        // 2. Load the new HTML content from the root path
        $mainContent.load(path, function(response, status, xhr) {
            if (status === "error") {
                console.error("Error loading page:", xhr.status, xhr.statusText);
                $mainContent.html('<h2>Page not found</h2><p>Could not load the requested content.</p>');
                return;
            }

            // 3. Load the corresponding script for the new page
            const pageName = getPageName(path);
            currentPage.name = pageName;
            currentPage.cleanup = function() {}; // Reset cleanup

            if (pageName && pageName !== 'dashboard' && pageName !== 'sensors') {
                 $.getScript(`/static/js/${pageName}.js`)
                    .done(function(script, textStatus) {
                        console.log(`Script for ${pageName} loaded successfully.`);
                    })
                    .fail(function(jqxhr, settings, exception) {
                        console.error(`Error loading script for ${pageName}:`, exception);
                    });
            }
        });
    }

    // --- Handle navigation clicks ---
    $('.sidebar a').on('click', function(e) {
        e.preventDefault();
        const path = $(this).attr('href');
        if (path === window.location.pathname) return; // Don't reload same page

        history.pushState({path: path}, '', path);
        loadPage(path);
        $('.sidebar a').removeClass('active');
        $(this).addClass('active');
    });

    // --- Handle browser back/forward buttons ---
    window.onpopstate = function(event) {
        if (event.state && event.state.path) {
            const path = event.state.path;
            loadPage(path);
            $('.sidebar a').removeClass('active');
            $(`.sidebar a[href="${path}"]`).addClass('active');
        }
    };

    // --- Initial page load ---
    // On first load, load the content for the current path
    const initialPath = window.location.pathname;
    const pathToLoad = (initialPath === '/' || initialPath === '') ? '/dashboard' : initialPath;

    // We don't load content on initial page load anymore,
    // because the server should render the initial content (if any).
    // Instead, we just set the active link.
    // If the server renders the full page, this script will re-load the content,
    // which is not ideal, but it's the trade-off for this routing model.
    loadPage(pathToLoad);
    $('.sidebar a').removeClass('active');
    $(`.sidebar a[href="${pathToLoad}"]`).addClass('active');
    history.replaceState({path: pathToLoad}, '', pathToLoad);
});
