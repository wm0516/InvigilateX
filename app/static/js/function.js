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

/* admin hompage tab function*/
document.addEventListener('DOMContentLoaded', function() {
    // Main navigation tabs
    const mainRouteToTab = {
        '/adminHome': 'admin_hometab',
        '/adminHome/upload': 'admin_uploadtab',
        '/adminHome/autoGenerate': 'admin_autoGeneratetab',
        '/adminHome/manageLecturer': 'admin_managetab',
    };

    // File upload sub-tabs
    const uploadRouteToTab = {
        '/adminHome/uploadLecturerTimetable': 'admin_uploadLecturerTimetabletab', 
        '/adminHome/uploadExamDetails': 'admin_uploadExamDetailstab',
    };

    const currentPath = window.location.pathname;
    
    // Handle main navigation tabs
    let activeMainTabId = 'admin_hometab';
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
    if (activeMainTabId === 'admin_uploadtab') {
        let activeUploadTabId = 'admin_uploadtab';
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




/* admin read upload file function */
function setupFileUpload({ formId, fileInputId, uploadUrl, resultDivId }) {
    const form = document.getElementById(formId);
    const fileInput = document.getElementById(fileInputId);
    const resultDiv = document.getElementById(resultDivId);

    // Debug: Verify elements exist
    if (!form) console.error(`Form with ID ${formId} not found`);
    if (!fileInput) console.error(`File input with ID ${fileInputId} not found`);
    if (!resultDiv) console.error(`Result div with ID ${resultDivId} not found`);
    if (!form || !fileInput || !resultDiv) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a file to upload.');
            return;
        }

        const formData = new FormData();
        const fileKey = fileInput.name;
        formData.append(fileKey, file);

        try {
            resultDiv.innerHTML = '<p>Uploading... please wait</p>';
            
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const data = await response.json();
                if (data.error) {
                    resultDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
                } else {
                    resultDiv.innerHTML = `
                        <p style="color:green;">${data.message || 'File uploaded successfully!'}</p>
                        ${data.columns ? `<strong>Columns:</strong> ${data.columns.join(', ')}<br>` : ''}
                        ${data.preview ? `<strong>Preview:</strong> <pre>${JSON.stringify(data.preview, null, 2)}</pre>` : ''}
                    `;
                    localStorage.setItem(fileKey + 'LastUploaded', new Date().toLocaleString());
                }
            } else {
                const text = await response.text();
                resultDiv.innerHTML = `<p>${text}</p>`;
            }
        } catch (err) {
            resultDiv.innerHTML = `<p style="color:red;">Upload failed: ${err.message}</p>`;
            console.error('Upload error:', err);
        }
    });
}

// Initialize both upload forms when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    // Lecturer timetable upload
    setupFileUpload({
        formId: 'uploadLecturerForm',
        fileInputId: 'lecturer_list',
        uploadUrl: 'adminHome/uploadLecturerTimetable',
        resultDivId: 'lecturerUploadResult'
    });

    // Exam details upload
    setupFileUpload({
        formId: 'uploadExamForm',
        fileInputId: 'exam_list',
        uploadUrl: 'adminHome/uploadExamDetails',
        resultDivId: 'examUploadResult' 
    });

    console.log('File upload forms initialized');
});