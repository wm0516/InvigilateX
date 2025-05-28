/* toggle function*/
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

/* tab function*/
document.addEventListener('DOMContentLoaded', function() {
    // Main navigation tabs
    const mainRouteToTab = {
        '/homepage': 'home',
        '/home/upload': 'upload',
        '/home/autoGenerate': 'autoGenerate',
        '/home/manageLecturer': 'manage',
    };

    // File upload sub-tabs
    const uploadRouteToTab = {
        '/home/uploadLecturerTimetable': 'uploadLecturerTimetable', // Fixed typo
        '/home/uploadExamDetails': 'uploadExamDetails',
    };

    const currentPath = window.location.pathname;
    
    // Handle main navigation tabs
    let activeMainTabId = 'home';
    for (const [route, tabId] of Object.entries(mainRouteToTab)) {
        if (currentPath.includes(route)) {
            activeMainTabId = tabId;
            break;
        }
    }

    // Update main tab UI
    document.querySelectorAll('.main-nav .tab-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-tab') === activeMainTabId) {
            link.classList.add('active');
        }
    });

    // Handle upload sub-tabs if we're in the upload section
    if (activeMainTabId === 'upload') {
        let activeUploadTabId = 'upload';
        for (const [route, tabId] of Object.entries(uploadRouteToTab)) {
            if (currentPath.includes(route)) {
                activeUploadTabId = tabId;
                break;
            }
        }

        // Update upload tab UI
        document.querySelectorAll('.upload-sub-nav .sub-tab-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-tab') === activeUploadTabId) {
                link.classList.add('active');
            }
        });
    }
});

/* read upload file function */
