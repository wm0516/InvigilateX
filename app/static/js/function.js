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
    '/admin/manageAccess': 'admin_manageAccesstab',
    '/admin/activity': 'admin_activitytab',
    '/admin/profile': 'admin_profiletab',

    '/user/home': 'user_hometab',
    '/user/ownTimetable': 'user_ownTimetabletab',
    '/user/mergeTimetable': 'user_mergeTimetabletab',
    '/user/invigilationReport': 'user_invigilationReporttab',
    '/user/invigilationTimetable': 'user_invigilationTimetabletab',
    '/user/profile': 'user_profiletab',
    '/user/viewStaff': 'user_viewStafftab'
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
    setupFileUpload('attendance_list', 'attendanceUploadContainer', 'attendanceSelectedFileName');
});


function searchContent() {
    const input = document.getElementById("searchInput");
    const noResults = document.getElementById("noResults");
    if (!input) return;
    const filter = input.value.toLowerCase();
    let anyVisible = false;

    const tables = ["manageCourse","manageDepartment","manageVenue","manageExam","manageStaff","viewStaff","activity","manageAccess"];
    for (const tableId of tables) {
        const table = document.getElementById(tableId);
        if (!table) continue;
        const rows = table.getElementsByTagName("tr");
        for (let i = 1; i < rows.length; i++) {
            const cells = rows[i].getElementsByTagName("td");
            let match = false;
            for (let j = 0; j < cells.length; j++) {
                if (cells[j].textContent.toLowerCase().includes(filter)) {
                    match = true;
                    break;
                }
            }
            rows[i].style.display = match ? "" : "none";
            if (match) anyVisible = true;
        }
    }

    if (noResults) noResults.style.display = anyVisible ? "none" : "block";
}

// Setup Function: Runs once per page
function setupSearch() {
    const input = document.getElementById("searchInput");
    const btn = document.getElementById("searchBtn");

    if (btn) btn.addEventListener("click", searchContent);
    if (input) input.addEventListener("keyup", searchContent);
}

// Auto-Initialize
document.addEventListener("DOMContentLoaded", setupSearch);




