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
    // Main navigation tabs
    const mainRouteToTab = {
        '/home_page': 'home',
        '/home/upload': 'upload',
        '/home/autoGenerate': 'autoGenerate',
        '/home/manageLecturer': 'manage',
    };

    // File upload sub-tabs (only relevant when in upload section)
    const uploadRouteToTab = {
        '/home/uploadLecturerTimetable': 'uploadlLecturerTimetable',
        '/home/uploadExamDetails': 'uploadExamDetails',
    };

    const currentPath = window.location.pathname;
    
    // First handle main navigation tabs
    let activeMainTabId = 'home'; // Default fallback
    for (const [route, tabId] of Object.entries(mainRouteToTab)) {
        if (currentPath.includes(route)) {
            activeMainTabId = tabId;
            break;
        }
    }

    // Update main tab UI only if elements exist
    const mainTabLinks = document.querySelectorAll('.main-nav .tab-link');
    if (mainTabLinks.length > 0) {
        mainTabLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-tab') === activeMainTabId) {
                link.classList.add('active');
            }
        });

        document.querySelectorAll('.main-tab-pane').forEach(pane => {
            pane.classList.remove('active');
            if (pane.id === activeMainTabId) {
                pane.classList.add('active');
            }
        });
    }

    // Then handle upload sub-tabs if we're in the upload section
    if (activeMainTabId === 'upload') {
        let activeUploadTabId = 'upload'; // Default fallback
        for (const [route, tabId] of Object.entries(uploadRouteToTab)) {
            if (currentPath.includes(route)) {
                activeUploadTabId = tabId;
                break;
            }
        }

        // Update upload tab UI only if elements exist
        const uploadTabLinks = document.querySelectorAll('.upload-sub-nav .tab-link');
        if (uploadTabLinks.length > 0) {
            uploadTabLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('data-tab') === activeUploadTabId) {
                    link.classList.add('active');
                }
            });

            document.querySelectorAll('.upload-tab-pane').forEach(pane => {
                pane.classList.remove('active');
                if (pane.id === activeUploadTabId) {
                    pane.classList.add('active');
                }
            });
        }
    }
});