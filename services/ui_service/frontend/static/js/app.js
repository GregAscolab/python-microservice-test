/**
 * app.js
 *
 * This script manages the Single Page Application (SPA) functionality.
 * It handles dynamic content loading and page-specific script management
 * for the App Shell architecture.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Get the main content area and all navigation links in the sidebar.
    const content = document.getElementById('content');
    const navLinks = document.querySelectorAll('.sidebar .nav-link');

    /**
     * Asynchronously loads page content into the main content area.
     * @param {string} url - The URL of the content to load.
     */
    const loadContent = async (url) => {
        try {
            // Fetch the HTML fragment from the server.
            // The 'content_only=true' query parameter tells the server to send back
            // just the page content, not the full layout.
            const response = await fetch(`${url}?content_only=true`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const html = await response.text();
            // Inject the fetched HTML into the content area.
            content.innerHTML = html;
            // Load any JavaScript specific to the new page.
            loadScriptsForPage(url);
        } catch (error) {
            console.error('Failed to load page: ', error);
            content.innerHTML = '<p>Error loading page. Please try again.</p>';
        }
    };

    /**
     * Loads and executes the JavaScript file associated with a given page.
     * @param {string} url - The URL of the page for which to load a script.
     */
    const loadScriptsForPage = (url) => {
        // Remove any previously loaded page-specific scripts to prevent conflicts.
        const existingScripts = document.querySelectorAll('[data-page-script]');
        existingScripts.forEach(script => script.remove());

        // Determine the script name from the URL. Defaults to 'dashboard'.
        const pageName = url.split('/').pop().split('.')[0] || 'dashboard';
        const scriptPath = `/static/js/${pageName}.js`;

        // Check if a script file actually exists before trying to load it.
        fetch(scriptPath, { method: 'HEAD' })
            .then(res => {
                if (res.ok) {
                    // If the script exists, create a new script element and append it to the body.
                    const script = document.createElement('script');
                    script.src = scriptPath;
                    script.setAttribute('data-page-script', 'true'); // Mark it for easy removal later.
                    script.onload = () => {
                        // Once the script is loaded, call the initialization function for the page.
                        const initFunctionName = `initialize${pageName.charAt(0).toUpperCase() + pageName.slice(1)}Page`;
                        console.log(`Calling ${initFunctionName}`);
                        if (typeof window[initFunctionName] === 'function') {
                            window[initFunctionName]();
                        } else {
                            console.log(`${initFunctionName} not found`);
                        }
                    };
                    document.body.appendChild(script);
                }
            })
            .catch(err => {
                // This is not necessarily an error, just means no specific script for this page.
                console.log(`No specific script for ${pageName}`);
            });
    };

    // Add click event listeners to all sidebar navigation links.
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent the default link navigation.
            const url = e.target.getAttribute('href');
            // Update the browser's history and URL without a full page reload.
            history.pushState({ path: url }, '', url);
            // Load the new content.
            loadContent(url);
        });
    });

    // Handle the browser's back and forward buttons.
    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.path) {
            loadContent(e.state.path);
        } else {
            // Fallback for the initial page load or when state is null.
            loadContent(location.pathname);
        }
    });

    // Load the initial content based on the current URL when the app first starts.
    // If the URL is '/', load the dashboard page.
    loadContent(location.pathname === '/' ? '/dashboard' : location.pathname);
});
