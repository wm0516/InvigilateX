/* toggle function */
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

/* register department text */
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
    '/adminHome/manageExam': 'admin_manageExamtab',
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
// Minimal JS for file name display and drag-drop styling
// Reusable function for setting up file upload UI
function setupFileUpload(fileInputId, uploadContainerId, fileNameDisplayId) {
    const fileInput = document.getElementById(fileInputId);
    const uploadContainer = document.getElementById(uploadContainerId);
    const fileNameDisplay = document.getElementById(fileNameDisplayId);

    if (!fileInput || !uploadContainer || !fileNameDisplay) return;

    // File selected via input
    fileInput.addEventListener('change', function () {
        if (this.files.length > 0) {
            fileNameDisplay.textContent = "Selected file: " + this.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
        }
    });

    // Drag and drop events
    uploadContainer.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadContainer.style.borderColor = '#5bc0de';
        uploadContainer.style.backgroundColor = '#e1f5fe';
    });

    uploadContainer.addEventListener('dragleave', function () {
        uploadContainer.style.borderColor = fileInput.files.length ? '#5cb85c' : '#ccc';
        uploadContainer.style.backgroundColor = fileInput.files.length ? '#e8f5e9' : '#f9f9f9';
    });

    uploadContainer.addEventListener('drop', function (e) {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = "Selected file: " + e.dataTransfer.files[0].name;
            uploadContainer.style.borderColor = '#5cb85c';
            uploadContainer.style.backgroundColor = '#e8f5e9';
        }
    });
}

// Initialize all upload components on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    setupFileUpload('course_list', 'courseUploadContainer', 'courseSelectedFileName');
    setupFileUpload('exam_list', 'examUploadContainer', 'examSelectedFileName');
    setupFileUpload('lecturer_list', 'lecturerUploadContainer', 'lecturerSelectedFileName');
    setupFileUpload('timetable_list', 'timetableUploadContainer', 'timetableSelectedFileName');
});





document.addEventListener("DOMContentLoaded", function () {
    const examDateInput = document.getElementById('examDate');
    const examDayInput = document.getElementById('examDay');
    const examDisplay = document.getElementById('examDisplay');

    const formatDate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const today = new Date();
    const minDate = formatDate(today);
    const nextYear = new Date(today);
    nextYear.setFullYear(today.getFullYear() + 1);
    const maxDate = formatDate(nextYear);

    examDateInput.min = minDate;
    examDateInput.max = maxDate;

    examDateInput.addEventListener('change', function () {
        const selectedDate = new Date(this.value);
        const day = selectedDate.getDay(); // 0 = Sunday, 6 = Saturday

        if (day === 0 || day === 6) {
            alert("Weekends are not allowed.");
            this.value = '';
            examDayInput.value = '';
            examDisplay.value = '';
            return;
        }

        const days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
        const formattedDate = formatDate(selectedDate);
        const dayName = days[day];

        examDayInput.value = dayName;
        examDisplay.value = `${formattedDate} ${dayName}`;
    });
});














