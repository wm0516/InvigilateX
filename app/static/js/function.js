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


/* Common Upload Functionality - Reusable */
function setupFileUpload(uploadContainerSelector, fileInputId, fileNameDisplayId) {
    const uploadContainer = document.querySelector(uploadContainerSelector);
    const fileInput = document.getElementById(fileInputId);
    const fileNameDisplay = document.getElementById(fileNameDisplayId);

    if (!uploadContainer || !fileInput || !fileNameDisplay) return;

    // Handle click on container
    uploadContainer.addEventListener('click', function(e) {
        // Only prevent default if clicking on the container itself, not its children
        if (e.target === uploadContainer) {
            e.preventDefault();
            fileInput.click();
        }
    });

    // Handle file selection
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileNameDisplay.textContent = "Selected file: " + this.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
            uploadContainer.classList.add('has-file'); // Add a class to mark as having file
        }
    });

    // Drag and drop functionality
    uploadContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadContainer.style.borderColor = '#5bc0de';
        uploadContainer.style.backgroundColor = '#e1f5fe';
    });

    uploadContainer.addEventListener('dragleave', function() {
        uploadContainer.style.borderColor = uploadContainer.classList.contains('has-file') ? '#5cb85c' : '#ccc';
        uploadContainer.style.backgroundColor = uploadContainer.classList.contains('has-file') ? '#e8f5e9' : '#f9f9f9';
    });

    uploadContainer.addEventListener('drop', function(e) {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = "Selected file: " + e.dataTransfer.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
            uploadContainer.classList.add('has-file'); // Add a class to mark as having file
        }
    });
}

/* Common Form Submission - Reusable */
async function handleFormSubmit(formId, fileInputId, resultDivId, errorDivId, tableBodySelector, fileFieldName, rowGenerator) {
    const form = document.getElementById(formId);
    const fileInput = document.getElementById(fileInputId);
    const resultDiv = document.getElementById(resultDivId);
    const errorDiv = document.getElementById(errorDivId);
    const tableBody = document.querySelector(tableBodySelector);

    if (!form || !fileInput || !resultDiv) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            resultDiv.innerHTML = '<p style="color:red;">Please select a file to upload.</p>';
            return;
        }

        const formData = new FormData();
        formData.append(fileFieldName, file);

        resultDiv.innerHTML = '<p>Uploading details... <span class="spinner">⌛</span></p>';
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
                            row.innerHTML = rowGenerator(i, record);
                            tableBody.appendChild(row);
                        });
                    }
                } else {
                    resultDiv.innerHTML = `<p style="color:orange;">${data.message}</p>`;
                    
                    if (data.errors && data.errors.length) {
                        errorDiv.innerHTML = '<ul>' + 
                            data.errors.map(err => `<li>${err}</li>`).join('') + 
                            '</ul>';
                    }
                }
                
                // Reset only the file input, keep the container styled
                fileInput.value = "";
                const fileNameDisplay = document.querySelector(`#${fileInputId}`).previousElementSibling;
                if (fileNameDisplay) fileNameDisplay.textContent = "";
                
                // Instead of resetting the container completely, just update the border
                const uploadContainer = document.querySelector(`#${fileInputId}`).closest('.upload-container');
                if (uploadContainer) {
                    uploadContainer.style.borderColor = '#ccc';
                    uploadContainer.style.backgroundColor = '#f9f9f9';
                    uploadContainer.classList.remove('has-file');
                }
            } else {
                const text = await response.text();
                resultDiv.innerHTML = `<p style="color:red;">Unexpected response: ${text}</p>`;
            }
        } catch (error) {
            resultDiv.innerHTML = `<p style="color:red;">Upload failed: ${error.message}</p>`;
            console.error('Upload error:', error);
        }
    });
}

// Initialize all upload forms when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Lecturer List Upload
    setupFileUpload('.upload-container', 'lecturerList_list', 'selectedFileName');
    handleFormSubmit('uploadLecturerListForm', 'lecturerList_list', 'lecturerListUploadResult', 
                   'lecturerListUploadErrors', '.user-data-table tbody', 'lecturerList_file', generateLecturerRow);

    // Lecturer Timetable Upload
    setupFileUpload('.upload-container', 'lecturer_list', 'selectedFileName');
    handleFormSubmit('uploadLecturerForm', 'lecturer_list', 'lecturerUploadResult', 
                   'lecturerUploadErrors', '.user-data-table tbody', 'lecturer_file', generateLecturerRow);

    // Exam Details Upload
    setupFileUpload('.upload-container', 'exam_list', 'selectedFileName');
    handleFormSubmit('uploadExamForm', 'exam_list', 'examUploadResult', 
                   'examUploadErrors', '.user-data-table tbody', 'exam_file', generateExamRow);

    // Course Details Upload
    setupFileUpload('.upload-container', 'course_list', 'selectedFileName');
    handleFormSubmit('uploadCourseForm', 'course_list', 'courseUploadResult', 
                   'courseUploadErrors', '.user-data-table tbody', 'course_file', generateExamRow);
});