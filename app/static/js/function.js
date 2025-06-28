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

function updateDepartmentLabel() {
    const roleSelect = document.getElementById('roleSelect');
    const departmentLabel = document.getElementById('departmentLabel');
    const selectedRole = roleSelect.value;
    
    switch(selectedRole) {
        case 'LECTURER':
            departmentLabel.textContent = 'Department';
            break;
        case 'DEAN':
            departmentLabel.textContent = 'Dean of Department';
            break;
        case 'HOP':
            departmentLabel.textContent = 'Head of Department';
            break;
        case 'ADMIN':
            departmentLabel.textContent = 'Admin of Department';
            break;
        default:
            departmentLabel.textContent = 'Department';
    }
}

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


/* hompage tab function*/
document.addEventListener('DOMContentLoaded', function() {
  const mainRouteToTab = {
    '/adminHome': 'admin_hometab',
    '/adminHome/uploadLecturerTimetable': 'admin_uploadLecturerTimetabletab',
    '/adminHome/uploadLecturerList': 'admin_uploadLecturerListtab',
    '/adminHome/uploadExamDetails': 'admin_uploadExamDetailstab',
    '/adminHome/manageCourse': 'admin_manageCoursetab',
    '/adminHome/autoGenerate': 'admin_autoGeneratetab',
    '/adminHome/manageLecturer': 'admin_manageLecturertab',    
    '/adminHome/viewReport': 'admin_viewReporttab',
    '/adminHome/manageDepartment': 'admin_manageDepartmenttab',

    '/lecturerHome': 'lecturer_hometab',
    '/lecturerHome/timetables': 'lecturer_timetabletab',
    '/lecturerHome/invigilationTimetable': 'lecturer_invigilationTimetabletab',
    '/lecturerHome/invigilationReport': 'lecturer_invigilationReporttab',
    '/lecturerHome/profile': 'lecturer_profiletab',

    'dean_homepage': 'dean_hometab',
    'dean_timetable': 'dean_timetabletab',
    'dean_invigilationReport': 'dean_invigilationReporttab',
    'dean_profile': 'dean_profiletab'
  };

  const currentPath = window.location.pathname;
  let activeMainTabId = null;

  for (const [route, tabId] of Object.entries(mainRouteToTab)) {
    if (currentPath.includes(route)) {
      activeMainTabId = tabId;
      break;
    }
  }

  // Only apply if a matching tabId was found
  if (activeMainTabId) {
    document.querySelectorAll('.main-nav .tab-link').forEach(link => {
      link.classList.toggle('active', link.getAttribute('data-tab') === activeMainTabId);
    });
  }
});






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
    setupFileUpload('.CourseUploadContainer', 'course_list', 'courseSelectedFileName');
    handleFormSubmit('uploadCourseForm', 'course_list', 'courseUploadResult', 
                 'courseUploadErrors', '.user-data-table tbody', 'course_file', generateCourseRow);

});


/* Common Upload Functionality - Reusable */
function setupFileUpload(uploadContainerSelector, fileInputId, fileNameDisplayId) {
    const uploadContainer = document.querySelector(uploadContainerSelector);
    const fileInput = document.getElementById(fileInputId);
    const fileNameDisplay = document.getElementById(fileNameDisplayId);

    if (!uploadContainer || !fileInput || !fileNameDisplay) return;

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
}

/* Common Form Submission - Reusable */
async function handleFormSubmit(formId, fileInputId, resultDivId, errorDivId, tableBodySelector, fileFieldName, generateRowFn) {
  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileInputId);
  const resultDiv = document.getElementById(resultDivId);
  const errorDiv = document.getElementById(errorDivId);
  const tableBody = document.querySelector(tableBodySelector);

  if (!form || !fileInput || !resultDiv) return;

  form.addEventListener('submit', async function(e) {
    const file = fileInput.files[0];
    const manualInputs = form.querySelectorAll('input[type="text"], input[type="number"]');
    const hasManualInput = Array.from(manualInputs).some(input => input.value.trim() !== "");

    // Mixed mode prevention
    if (file && hasManualInput) {
      e.preventDefault();
      errorDiv.innerHTML = '<p style="color:red;">Please use either file upload OR manual input, not both.</p>';
      return;
    }

    // FILE UPLOAD mode
    if (file) {
      e.preventDefault();
      const formData = new FormData();
      formData.append(fileFieldName, file);

      resultDiv.textContent = '';
      errorDiv.textContent = '';
      const spinner = document.createElement('span');
      spinner.className = 'spinner';
      spinner.textContent = '⌛ Uploading...';
      resultDiv.appendChild(spinner);

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: formData
        });

        resultDiv.textContent = '';
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await response.json();
          if (data.success) {
            const msg = document.createElement('p');
            msg.style.color = 'green';
            msg.textContent = data.message;
            resultDiv.appendChild(msg);

            if (Array.isArray(data.records) && data.records.length && tableBody) {
              tableBody.innerHTML = '';
              data.records.forEach((rec, i) => {
                const row = document.createElement('tr');
                row.innerHTML = generateRowFn(i, rec);
                tableBody.appendChild(row);
              });
            }
          } else {
            const msg = document.createElement('p');
            msg.style.color = 'orange';
            msg.textContent = data.message;
            resultDiv.appendChild(msg);

            if (Array.isArray(data.errors)) {
              const ul = document.createElement('ul');
              data.errors.forEach(err => {
                const li = document.createElement('li');
                li.textContent = err;
                ul.appendChild(li);
              });
              errorDiv.appendChild(ul);
            }
          }

          fileInput.value = '';
          const fileNameDisplay = document.getElementById('selectedFileName');
          if (fileNameDisplay) fileNameDisplay.textContent = '';
          const uploadContainer = document.querySelector(`#${fileInputId}`).closest('.upload-container');
          if (uploadContainer) {
            uploadContainer.style.borderColor = '#ccc';
            uploadContainer.style.backgroundColor = '#f9f9f9';
          }

        } else {
          const text = await response.text();
          const p = document.createElement('p');
          p.style.color = 'red';
          p.textContent = `Unexpected response: ${text}`;
          resultDiv.appendChild(p);
        }

      } catch (err) {
        resultDiv.textContent = '';
        const p = document.createElement('p');
        p.style.color = 'red';
        p.textContent = `Upload failed: ${err.message}`;
        resultDiv.appendChild(p);
      }

    } else {
      // MANUAL mode: allow normal POST to Flask
      return; // Do not call preventDefault()
    }
  });

}


// Custom row generators for different forms
function generateLecturerRow(index, record) {
    return `
        <td>${index + 1}</td>
        <td>${record.ID}</td>
        <td>${record.Name}</td>
        <td>${record.Department}</td>
        <td>${record.Role}</td>
        <td>${record.Email}</td>
        <td>${record.Contact}</td>
        <td>Deactivated</td>
    `;
}

function generateExamRow(index, record) {
    return `
        <td>${index + 1}</td>
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
}

function generateCourseRow(index, record) {
    return `
        <td>${index + 1}</td>
        <td>${record.code}</td>
        <td>${record.section}</td>
        <td>${record.name}</td>
        <td>${record.creditHour}</td>
    `;
}

/*function generateTimetableRow(index, record) {
    return `
        <td>${index + 1}</td>
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
}*/



