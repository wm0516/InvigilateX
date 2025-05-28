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
document.addEventListener('DOMContentLoaded', function() {
    setupExamDetails();

    const examLastUploaded = localStorage.getItem('examLastUploaded');
    if (examLastUploaded) {
        const examLastUploadedLabel = document.getElementById('examLastUploadedLabel');
        if (examLastUploadedLabel) {
            examLastUploadedLabel.textContent = `Last Uploaded: ${examLastUploaded}`;
        }
    }
});

function setupExamDetails() {
    const uploadExamDetails = document.getElementById('uploadExamDetails');    
    if (uploadExamDetails && !uploadExamDetails.dataset.listenerAttached) {
        uploadExamDetails.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const file = document.getElementById('exam_file').files[0];

            if (!file) {
                alert('Please select a file');
                return;
            }

            fetch('/home/uploadExamDetails', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.redirected) {
                    // Handle Flask redirect (for flash messages)
                    window.location.href = response.url;
                    return;
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    alert(data.message);
                    if (data.warnings) {
                        data.warnings.forEach(warning => alert('Warning: ' + warning));
                    }
                    const currentDate = new Date();
                    const formattedDate = currentDate.toLocaleString('en-GB', {
                        weekday: 'short', year: '2-digit', month: 'short', day: '2-digit',
                        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
                    });
                    localStorage.setItem('examLastUploaded', formattedDate);
                    window.location.reload(true);
                }
            })
            .catch(error => {
                alert('Upload failed: ' + error.message);
            });
        });
        uploadExamDetails.dataset.listenerAttached = "true";
    }
}