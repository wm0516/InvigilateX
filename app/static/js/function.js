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
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('exam_list');
    const resultDiv = document.getElementById('uploadResult');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];

        if (!file) {
        alert('Please select a file to upload.');
        return;
        }

        // Create a new FormData object and append the file manually
        const formData = new FormData();
        formData.append('exam_file', file);

        try {
        const response = await fetch('/home/uploadExamDetails', {
            method: 'POST',
            body: formData
            // IMPORTANT: Do NOT set Content-Type header manually when sending FormData!
        });

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await response.json();
            if (data.error) {
            resultDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
            } else {
            resultDiv.innerHTML = `
                <p style="color:green;">${data.message}</p>
                <strong>Columns:</strong> ${data.columns ? data.columns.join(', ') : 'N/A'}<br>
                <strong>Preview:</strong> <pre>${data.preview ? JSON.stringify(data.preview, null, 2) : ''}</pre>
            `;
            localStorage.setItem('examLastUploaded', new Date().toLocaleString());
            }
        } else {
            const text = await response.text();
            resultDiv.innerHTML = `<p>${text}</p>`;
        }
        } catch (err) {
        alert('Upload failed: ' + err.message);
        }
    });
});
