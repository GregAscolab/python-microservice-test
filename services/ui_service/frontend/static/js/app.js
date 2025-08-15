document.addEventListener('DOMContentLoaded', () => {
    const content = document.getElementById('content');
    const navLinks = document.querySelectorAll('.sidebar .nav-link');

    const loadContent = async (url) => {
        try {
            // Add 'content_only=true' to the URL to get just the HTML fragment
            const response = await fetch(`${url}?content_only=true`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const html = await response.text();
            content.innerHTML = html;
            // After loading content, we might need to re-initialize scripts for that content
            // This will be handled by a script loader function if necessary
            loadScriptsForPage(url);
        } catch (error) {
            console.error('Failed to load page: ', error);
            content.innerHTML = '<p>Error loading page. Please try again.</p>';
        }
    };

    const loadScriptsForPage = (url) => {
        // Remove existing page-specific scripts to avoid conflicts
        const existingScripts = document.querySelectorAll('[data-page-script]');
        existingScripts.forEach(script => script.remove());

        const pageName = url.split('/').pop().split('.')[0] || 'dashboard'; // Default to dashboard
        const scriptPath = `/static/js/${pageName}.js`;

        // Check if a script for this page exists, then load it
        fetch(scriptPath, { method: 'HEAD' })
            .then(res => {
                if (res.ok) {
                    const script = document.createElement('script');
                    script.src = scriptPath;
                    script.setAttribute('data-page-script', 'true'); // Mark as a page-specific script
                    document.body.appendChild(script);
                }
            })
            .catch(err => {
                console.log(`No specific script for ${pageName}`);
            });
    };

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const url = e.target.getAttribute('href');
            history.pushState({ path: url }, '', url);
            loadContent(url);
        });
    });

    // Handle back/forward browser navigation
    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.path) {
            loadContent(e.state.path);
        } else {
            // Fallback for initial page load
            loadContent(location.pathname);
        }
    });

    // Load initial content based on the current URL
    loadContent(location.pathname === '/' ? '/dashboard' : location.pathname);
});
