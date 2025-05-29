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




/* Lecturer Timetable Upload - Self-contained */
// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', setupLecturerUpload);
function setupLecturerUpload() {
    const form = document.getElementById('/adminHome/uploadLecturerTimetable');
    const fileInput = document.getElementById('lecturer_list');
    const resultDiv = document.getElementById('lecturerUploadResult');

    // Debug: Verify elements exist
    if (!form) console.error('Form with ID /adminHome/uploadLecturerTimetable not found');
    if (!fileInput) console.error('File input with ID lecturer_list not found');
    if (!resultDiv) console.error('Result div with ID lecturerUploadResult not found');
    if (!form || !fileInput || !resultDiv) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a lecturer timetable file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('lecturer_list', file);

        try {
            resultDiv.innerHTML = '<p>Uploading lecturer timetable... please wait</p>';
            
            const response = await fetch('/adminHome/uploadLecturerTimetable', {
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
                        <p style="color:green;">${data.message || 'Lecturer timetable uploaded successfully!'}</p>
                        ${data.columns ? `<strong>Columns:</strong> ${data.columns.join(', ')}<br>` : ''}
                        ${data.preview ? `<strong>Preview:</strong> <pre>${JSON.stringify(data.preview, null, 2)}</pre>` : ''}
                    `;
                    localStorage.setItem('lecturer_listLastUploaded', new Date().toLocaleString());
                }
            } else {
                const text = await response.text();
                resultDiv.innerHTML = `<p>${text}</p>`;
            }
        } catch (err) {
            resultDiv.innerHTML = `<p style="color:red;">Upload failed: ${err.message}</p>`;
            console.error('Lecturer upload error:', err);
        }
    });
}



/* Exam Details Upload - Self-contained */
// Initialize when DOM is loaded


document.addEventListener('DOMContentLoaded', setupExamUpload);

function setupExamUpload() {
    const form = document.getElementById('uploadExamForm');
    const fileInput = document.getElementById('exam_list');
    const resultDiv = document.getElementById('examUploadResult');
    const tableBody = document.querySelector('.user-data-table tbody');

    if (!form || !fileInput || !resultDiv || !tableBody) {
        console.error('One or more elements not found');
        return;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            alert('Please select an exam file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('exam_file', file);

        resultDiv.innerHTML = '<p>Uploading exam details... please wait</p>';

        try {
            const response = await fetch('/adminHome/uploadExamDetails', {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('content-type') || '';

            if (contentType.includes('application/json')) {
                const data = await response.json();

                resultDiv.innerHTML = `<p style="color:${data.success ? 'green' : 'orange'};">${data.message}</p>`;

                if (data.success && Array.isArray(data.records) && data.records.length > 0) {
                    data.records.forEach(record => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${record.Date}</td>
                            <td>${record.Day}</td>
                            <td>${record.Start}</td>
                            <td>${record.End}</td>
                            <td>${record.Program}</td>
                            <td>${record["Course/Sec"]}</td>
                            <td>${record.Lecturer}</td>
                            <td>${record["No Of"]}</td>
                            <td>${record.Room}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                }

                // Optional: show errors
                if (data.errors && data.errors.length > 0) {
                    resultDiv.innerHTML += `
                        <strong style="color:red;">Errors:</strong>
                        <ul>${data.errors.map(err => `<li>${err}</li>`).join('')}</ul>
                    `;
                }

                fileInput.value = ""; // Clear file input
            } else {
                const text = await response.text();
                resultDiv.innerHTML = `<p>${text}</p>`;
            }
        } catch (error) {
            resultDiv.innerHTML = `<p style="color:red;">Upload failed: ${error.message}</p>`;
            console.error(error);
        }
    });
}

