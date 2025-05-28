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
document.addEventListener('DOMContentLoaded', function () {
    setupExamDetails();

    // Optional: Load and display the last uploaded info
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
        uploadExamDetails.addEventListener('submit', function (e) {
            e.preventDefault();

            const fileInput = document.getElementById('exam_list');
            const file = fileInput.files[0];

            if (!file) {
                alert('Please select a file to upload.');
                return;
            }

            // Create FormData from the form — includes all fields
            const form = document.getElementById('uploadExamDetails');
            const formData = new FormData(form);

            fetch('/home/uploadExamDetails', {
                method: 'POST',
                body: formData,
                // DO NOT manually set headers; let the browser handle multipart/form-data
            })
                .then(response => {
                    if (response.redirected) {
                        window.location.href = response.url;
                        return;
                    }
                    return response.json(); // If your Flask route returns JSON
                })
                .then(data => {
                    // Optional: Handle the response JSON here
                    console.log('Upload response:', data);
                    alert('File uploaded successfully!');
                    localStorage.setItem('examLastUploaded', new Date().toLocaleString());
                })
                .catch(error => {
                    console.error('Error during upload:', error);
                    alert('Upload failed: ' + error.message);
                });
        });

        // Prevent multiple bindings
        uploadExamDetails.dataset.listenerAttached = 'true';
    }
}