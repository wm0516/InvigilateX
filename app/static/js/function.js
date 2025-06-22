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


// Initialize sidebar state from localStorage
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }
});


// Optional JavaScript for drag and drop functionality
const uploadContainer = document.querySelector('.upload-container');

uploadContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = '#0066ff';
    uploadContainer.style.backgroundColor = '#f0f7ff';
});

uploadContainer.addEventListener('dragleave', () => {
    uploadContainer.style.borderColor = '#ccc';
    uploadContainer.style.backgroundColor = '#f9f9f9';
});

uploadContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = '#ccc';
    uploadContainer.style.backgroundColor = '#f9f9f9';
    
    // Handle dropped files
    const fileInput = document.getElementById('file-input');
    fileInput.files = e.dataTransfer.files;
    
    // Optional: display file name or trigger upload
    if (fileInput.files.length > 0) {
        console.log('File selected:', fileInput.files[0].name);
        // Here you could add code to upload the file
    }
});

// funtion of toggle side bar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    // Save state to localStorage
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}



/* admin hompage tab function*/
document.addEventListener('DOMContentLoaded', function() {
  const mainRouteToTab = {
    '/adminHome': 'admin_hometab',
    '/adminHome/uploadLecturerTimetable': 'admin_uploadLecturerTimetabletab',
    '/adminHome/uploadLecturerList': 'admin_uploadLecturerListtab',
    '/adminHome/uploadExamDetails': 'admin_uploadExamDetailstab',
    '/adminHome/uploadCourseDetails': 'admin_uploadCourseDetailstab',
    '/adminHome/autoGenerate': 'admin_autoGeneratetab',
    '/adminHome/manageLecturer': 'admin_managetab'
  };

  const currentPath = window.location.pathname;
  let activeMainTabId = 'admin_hometab';

  for (const [route, tabId] of Object.entries(mainRouteToTab)) {
    if (currentPath.includes(route)) {
      activeMainTabId = tabId;
      break;
    }
  }

  document.querySelectorAll('.main-nav .tab-link').forEach(link => {
    link.classList.toggle('active', link.getAttribute('data-tab') === activeMainTabId);
  });
});





/* Lecturer List Upload - Self-contained */
// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', setupLecturerListUpload);
function setupLecturerListUpload() {
    const form = document.getElementById('uploadLecturerListForm');
    const fileInput = document.getElementById('lecturerList_list');
    const resultDiv = document.getElementById('lecturerListUploadResult');
    const tableBody = document.querySelector('.user-data-table tbody');

    if (!form || !fileInput || !resultDiv || !tableBody) {
        console.error('One or more elements not found');
        return;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            alert('Please select an lecturer file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('lecturerList_file', file);

        resultDiv.innerHTML = '<p>Uploading lecturer details... please wait</p>';

        try {
            const response = await fetch('/adminHome/uploadLecturerList', {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('content-type') || '';
             if (contentType.includes('application/json')) {
                const data = await response.json();
                const errorDiv = document.getElementById('lecturerListUploadErrors');
                resultDiv.innerHTML = `<p style="color:${data.success ? 'green' : 'orange'};">${data.message}</p>`;
                errorDiv.innerHTML = ''; // Clear previous

                if (data.success && Array.isArray(data.records) && data.records.length > 0) {
                    tableBody.innerHTML = ''; // Clear existing table content before rendering new data
                    data.records.forEach((record, i) => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${i + 1}</td> <!-- Row number starting from 1 -->
                            <td>${record.ID}</td>
                            <td>${record.Name}</td>
                            <td>${record.Department}</td>
                            <td>${record.Role}</td>
                            <td>${record.Email}</td>
                            <td>${record.Contact}</td>
                            <td>Deactivated</td>
                        `;
                        tableBody.appendChild(row);
                    });
                } else {
                    const errorList = data.errors && data.errors.length
                        ? '<ul>' + data.errors.map(err => `<li>${err}</li>`).join('') + '</ul>'
                        : '<p>No data uploaded. All entries may be duplicates or invalid.</p>';

                    errorDiv.innerHTML = `<div style="color: red;">${errorList}</div>`;
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




/* Lecturer Timetable Upload - Self-contained */
// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadLecturerForm');
    const fileInput = document.getElementById('lecturer_list');
    const uploadContainer = document.querySelector('.upload-container');
    const fileNameDisplay = document.getElementById('selectedFileName');
    const resultDiv = document.getElementById('lecturerUploadResult');
    const errorDiv = document.getElementById('lecturerUploadErrors');
    const tableBody = document.querySelector('.user-data-table tbody');

    // Handle click on container
    uploadContainer.addEventListener('click', function(e) {
        e.preventDefault();
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileNameDisplay.textContent = "Selected file: " + this.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
        }
    });

    // Drag and drop functionality
    uploadContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadContainer.style.borderColor = '#5bc0de';
        uploadContainer.style.backgroundColor = '#e1f5fe';
    });

    uploadContainer.addEventListener('dragleave', function() {
        uploadContainer.style.borderColor = fileInput.files.length ? '#5cb85c' : '#ccc';
        uploadContainer.style.backgroundColor = fileInput.files.length ? '#e8f5e9' : '#f9f9f9';
    });

    uploadContainer.addEventListener('drop', function(e) {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = "Selected file: " + e.dataTransfer.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
        }
    });

    // Form submission handling
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            resultDiv.innerHTML = '<p style="color:red;">Please select a file to upload.</p>';
            return;
        }

        const formData = new FormData();
        formData.append('lecturer_file', file);

        resultDiv.innerHTML = '<p>Uploading lecturer details... <span class="spinner"></span></p>';
        errorDiv.innerHTML = '';

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const data = await response.json();
                
                if (data.success) {
                    resultDiv.innerHTML = `<p style="color:green;">${data.message}</p>`;
                    
                    // Update table if data exists
                    if (Array.isArray(data.records) && data.records.length > 0 && tableBody) {
                        tableBody.innerHTML = '';
                        data.records.forEach((record, i) => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${i + 1}</td>
                                <td>${record.ID}</td>
                                <td>${record.Name}</td>
                                <td>${record.Department}</td>
                                <td>${record.Role}</td>
                                <td>${record.Email}</td>
                                <td>${record.Contact}</td>
                                <td>Deactivated</td>
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                } else {
                    resultDiv.innerHTML = `<p style="color:orange;">${data.message}</p>`;
                    
                    // Display errors if they exist
                    if (data.errors && data.errors.length) {
                        errorDiv.innerHTML = '<ul>' + 
                            data.errors.map(err => `<li>${err}</li>`).join('') + 
                            '</ul>';
                    }
                }
                
                // Reset file input
                fileInput.value = "";
                fileNameDisplay.textContent = "";
                uploadContainer.style.borderColor = '#ccc';
                uploadContainer.style.backgroundColor = '#f9f9f9';
            } else {
                const text = await response.text();
                resultDiv.innerHTML = `<p style="color:red;">Unexpected response: ${text}</p>`;
            }
        } catch (error) {
            resultDiv.innerHTML = `<p style="color:red;">Upload failed: ${error.message}</p>`;
            console.error('Upload error:', error);
        }
    });
});


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
                const errorDiv = document.getElementById('examUploadErrors');
                resultDiv.innerHTML = `<p style="color:${data.success ? 'green' : 'orange'};">${data.message}</p>`;
                errorDiv.innerHTML = ''; // Clear previous

                 if (data.success && Array.isArray(data.records) && data.records.length > 0) {
                    tableBody.innerHTML = ''; // Clear existing table content before rendering new data
                    data.records.forEach((record, i) => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${i + 1}</td> <!-- Row number starting from 1 -->
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
                } else {
                    const errorList = data.errors && data.errors.length
                        ? '<ul>' + data.errors.map(err => `<li>${err}</li>`).join('') + '</ul>'
                        : '<p>No data uploaded. All entries may be duplicates or invalid.</p>';

                    errorDiv.innerHTML = `<div style="color: red;">${errorList}</div>`;
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

