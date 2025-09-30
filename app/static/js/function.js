// Function for Toggle Button 
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


// Register Page: Department Text [Will Changes According to Role]
function updateDepartmentLabel() {
    const roleSelect = document.getElementById('roleSelect');
    const departmentLabel = document.getElementById('departmentLabel');
    const selectedRole = roleSelect.value;
    
    switch(selectedRole) {
        case 'LECTURER':
            departmentLabel.textContent = 'Lecturer of Department';
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


// To All Page Exclude 'Auth Page': Initialize sidebar state from localStorage
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }
});


// Funtion of toggle side bar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    // Save state to localStorage
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}


// Homepage Tab Function
document.addEventListener('DOMContentLoaded', function() {
  const mainRouteToTab = {
    '/admin/home': 'admin_hometab',
    '/admin/manageTimetable': 'admin_manageTimetabletab',
    '/admin/manageExam': 'admin_manageExamtab',
    '/admin/manageCourse': 'admin_manageCoursetab',
    '/admin/manageInvigilationTimetable': 'admin_manageInvigilationTimetabletab',
    '/admin/manageStaff': 'admin_manageStafftab',    
    '/admin/manageInvigilationReport': 'admin_manageInvigilationReporttab',
    '/admin/manageDepartment': 'admin_manageDepartmenttab',
    '/admin/manageVenue': 'admin_manageVenuetab',

    '/lecturer/home': 'lecturer_hometab',
    '/lecturer/timetable': 'lecturer_timetabletab',
    '/lecturer/invigilationTimetable': 'lecturer_invigilationTimetabletab',
    '/lecturer/invigilationReport': 'lecturer_invigilationReporttab',
    '/lecturer/profile': 'lecturer_profiletab',

    '/dean/home': 'dean_hometab',
    '/dean/timetable': 'dean_timetabletab',
    '/dean/invigilationReport': 'dean_invigilationReporttab',
    '/dean/profile': 'dean_profiletab',
    '/dean/mergeTimetable': 'dean_mergeTimetabletab',

    '/hop/home': 'hop_hometab',
    '/hop/timetable': 'hop_timetabletab',
    '/hop/invigilationReport': 'hop_invigilationReporttab',
    '/hop/profile': 'hop_profiletab'
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


// Second Navigation Tab For Certain Page
document.addEventListener("DOMContentLoaded", function () {
    const tabLinks = document.querySelectorAll(".second-nav .tab-link");
    const tabKey = window.location.pathname + "_activeTab"; // Unique key per page

    function showSection(sectionId, event) {
        if (event) event.preventDefault();

        ["dashboardForm", "uploadForm", "manualForm","editForm"].forEach(formId => {
            const form = document.getElementById(formId);
            if (form) form.style.display = "none";
        });

        const selectedForm = document.getElementById(sectionId.replace("Section", "Form"));
        if (selectedForm) {
            selectedForm.style.display = "block";

            tabLinks.forEach(tab => tab.classList.remove("active"));
            const clickedTab = Array.from(tabLinks).find(tab => tab.dataset.section === sectionId);
            if (clickedTab) clickedTab.classList.add("active");

            // Save the current tab to sessionStorage using a page-specific key
            sessionStorage.setItem(tabKey, sectionId);
        } else {
            console.warn("Section not found:", sectionId);
        }
    }

    // Attach tab link click listeners
    tabLinks.forEach(tab => {
        tab.addEventListener("click", function (event) {
            showSection(this.dataset.section, event);
        });
    });

    // Determine the correct section to show on load
    const savedSection = sessionStorage.getItem(tabKey);

    // Check if the saved section actually exists on this page
    const availableForms = ["dashboardForm", "uploadForm", "manualForm","editForm"].filter(id => document.getElementById(id));
    const defaultSection = availableForms.length > 0 ? availableForms[0].replace("Form", "Section") : null;

    if (savedSection && document.getElementById(savedSection.replace("Section", "Form"))) {
        showSection(savedSection);
    } else if (defaultSection) {
        showSection(defaultSection);
    }
});


// Admin Page: Function of Upload File 
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
    setupFileUpload('staff_list', 'staffUploadContainer', 'staffSelectedFileName');
    setupFileUpload('timetable_list', 'timetableUploadContainer', 'timetableSelectedFileName');
});


// Admin Manage Exam Page(Manual): Function to track the selected date and display out the day
document.addEventListener("DOMContentLoaded", function() {
    const startDate = document.getElementById("startDate");
    const startTime = document.getElementById("startTime");
    const endDate = document.getElementById("endDate");
    const endTime = document.getElementById("endTime");

    const now = new Date();
    const today = now.toISOString().split("T")[0];
    const nextYear = new Date(now);
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    const nextYearDate = nextYear.toISOString().split("T")[0];

    // Restrict date pickers
    startDate.min = today;
    startDate.max = nextYearDate;
    endDate.min = today;
    endDate.max = nextYearDate;

    // Default: set both dates to today
    startDate.value = today;
    endDate.value = today;

    // Restrict time: disable past times if today is selected
    function restrictStartTime() {
        if (startDate.value === today) {
            let hh = String(now.getHours()).padStart(2, "0");
            let mm = String(now.getMinutes()).padStart(2, "0");
            startTime.min = hh + ":" + mm;  // from now onwards
        } else {
            startTime.min = "00:00"; // full day allowed
        }
    }

    function restrictEndTime() {
        if (endDate.value === today) {
            let hh = String(now.getHours()).padStart(2, "0");
            let mm = String(now.getMinutes()).padStart(2, "0");
            endTime.min = hh + ":" + mm;
        } else {
            endTime.min = "00:00";
        }
    }

    // Adjust end date automatically
    function adjustEndDate() {
        if (!startDate.value || !startTime.value || !endTime.value) return;

        const start = new Date(startDate.value + "T" + startTime.value);
        let end = new Date(endDate.value + "T" + endTime.value);

        // If end time is earlier than start time → assume overnight
        if (end < start) {
            let nextDay = new Date(start);
            nextDay.setDate(nextDay.getDate() + 1);
            endDate.value = nextDay.toISOString().split("T")[0];
        } else {
            endDate.value = startDate.value;
        }
    }

    // Bind events
    startDate.addEventListener("change", () => {
        endDate.value = startDate.value;
        restrictStartTime();
        restrictEndTime();
    });
    endDate.addEventListener("change", restrictEndTime);
    startTime.addEventListener("change", adjustEndDate);
    endTime.addEventListener("change", adjustEndDate);

    // Initial restriction setup
    restrictStartTime();
    restrictEndTime();
});









