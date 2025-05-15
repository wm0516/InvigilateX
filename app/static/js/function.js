document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('.toggle-password-btn');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });
});

/*
// Simple tab switching functionality
document.addEventListener('DOMContentLoaded', function() {
    const tabLinks = document.querySelectorAll('.tab-link');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs and panes
            document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
});
*/

document.addEventListener('DOMContentLoaded', function() {
    // Map URL endpoints to tab IDs
    const routeToTab = {
        '/home_page': 'home',
        '/home/uploadFile': 'upload',
        '/home/examInput': 'exam',
        '/home/autoGenerate': 'generate',
        '/home/assignLecturer': 'settings'
    };

    // Get current path and find matching tab
    const currentPath = window.location.pathname;
    let activeTabId = 'home'; // Default fallback

    for (const [route, tabId] of Object.entries(routeToTab)) {
        if (currentPath.includes(route)) {
            activeTabId = tabId;
            break;
        }
    }

    // Update active tab UI
    document.querySelectorAll('.tab-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-tab') === activeTabId) {
            link.classList.add('active');
        }
    });

    // Optional: Highlight corresponding tab content pane
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
        if (pane.id === activeTabId) {
            pane.classList.add('active');
        }
    });
});