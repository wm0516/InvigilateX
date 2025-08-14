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
    '/adminHome': 'admin_hometab',
    '/adminHome/manageTimetable': 'admin_manageTimetabletab',
    '/adminHome/manageExam': 'admin_manageExamtab',
    '/adminHome/manageCourse': 'admin_manageCoursetab',
    '/adminHome/manageInvigilationTimetable': 'admin_manageInvigilationTimetabletab',
    '/adminHome/manageLecturer': 'admin_manageLecturertab',    
    '/adminHome/manageInvigilationReport': 'admin_manageInvigilationReporttab',
    '/adminHome/manageDepartment': 'admin_manageDepartmenttab',
    '/adminHome/manageVenue': 'admin_manageVenuetab',

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


// Second Navigation Tab For Certain Page
document.addEventListener("DOMContentLoaded", function () {
    const tabLinks = document.querySelectorAll(".second-nav .tab-link");

    function showSection(sectionId, event) {
        if (event) event.preventDefault();

        ["announceForm", "uploadForm", "manualForm"].forEach(formId => {
            const form = document.getElementById(formId);
            if (form) form.style.display = "none";
        });

        const selectedForm = document.getElementById(sectionId.replace("Section", "Form"));
        if (selectedForm) selectedForm.style.display = "block";

        tabLinks.forEach(tab => tab.classList.remove("active"));
        const clickedTab = Array.from(tabLinks).find(tab => tab.dataset.section === sectionId);
        if (clickedTab) clickedTab.classList.add("active");
    }

    // Attach click listeners
    tabLinks.forEach(tab => {
        tab.addEventListener("click", function (event) {
            showSection(this.dataset.section, event);
        });
    });

    // ✅ Always show default section on page load
    showSection("announceSection");
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
    setupFileUpload('lecturer_list', 'lecturerUploadContainer', 'lecturerSelectedFileName');
    setupFileUpload('timetable_list', 'timetableUploadContainer', 'timetableSelectedFileName');
});


// Admin Manage Exam Page: Function to track the selected date and display out the day
document.addEventListener("DOMContentLoaded", function () {
    const examDateInput = document.getElementById('examDate');
    const examDayInput = document.getElementById('examDay');

    if (!examDateInput || !examDayInput) {
        return; // Exit if not on the exam page
    }

    const formatDate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const today = new Date();
    const minDate = formatDate(today);
    const nextYearSameDay = new Date(today);
    nextYearSameDay.setFullYear(today.getFullYear() + 1);
    const maxDate = formatDate(nextYearSameDay);

    examDateInput.min = minDate;
    examDateInput.max = maxDate;

    examDateInput.addEventListener('change', function () {
        const selectedDate = new Date(this.value);
        const day = selectedDate.getDay();

        const selected = formatDate(selectedDate);
        if (selected < minDate || selected > maxDate) {
            alert("Date must be within one year from today.");
            this.value = '';
            examDayInput.value = '';
            return;
        }

        const days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
        examDayInput.value = days[day];
    });
});


// Admin Manage Exam Page: Function to Read Selected "Department Code" and related "Course Code" will be displayed out
document.addEventListener("DOMContentLoaded", function() {
    const programCode = document.getElementById('programCode');
    if (!programCode) return; // Stop here if not on this page

    programCode.addEventListener('change', function() {
        let deptCode = this.value;
        let courseSectionSelect = document.getElementById('courseSection');
        let practicalLecturerSelect = document.getElementById('practicalLecturer');
        let tutorialLecturerSelect = document.getElementById('tutorialLecturer');
        let studentSelect = document.getElementById('student');

        courseSectionSelect.innerHTML = '<option value="" disabled selected>Select Course Section</option>';
        practicalLecturerSelect.value = "";
        tutorialLecturerSelect.value = "";
        studentSelect.value = "";

        if (deptCode) {
            fetch(`/get_courses_by_department/${deptCode}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(course => {
                        let option = document.createElement('option');
                        option.value = course.courseCodeSection;
                        option.textContent = course.courseCodeSection;
                        courseSectionSelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error fetching courses:', error));
        }
    });
});


// Admin Manage Exam Page: Function to Read Selected "Course Code Section" and related "Total of Students, Practical and Tutorial Lecturer" will be displayed out
document.addEventListener("DOMContentLoaded", function () {
    const courseSectionEl = document.getElementById('courseSection');
    if (!courseSectionEl) {
        console.error("courseSection element not found in DOM.");
        return;
    }

    courseSectionEl.addEventListener('change', function() {
        let deptCode = document.getElementById('programCode')?.value || "";
        let sectionCode = document.getElementById('courseSection')?.value || "";
        console.log("Selected:", deptCode, sectionCode);

        if (deptCode && sectionCode) {
            fetch(`/get_course_details/${deptCode}/${encodeURIComponent(sectionCode)}`)
                .then(response => {
                    if (!response.ok) throw new Error("API failed");
                    return response.json();
                })
                .then(data => {
                    console.log("API Data:", data);
                    document.getElementById('practicalLecturer').value = data.practicalLecturer || "";
                    document.getElementById('tutorialLecturer').value = data.tutorialLecturer || "";
                    document.getElementById('student').value = data.student || "";
                })
                .catch(err => console.error("Error:", err));
        }
    });
});


// Admin Manage Course Page: Function to Read Selected "Department Code" and related "Lecturer" will be displayed out
document.addEventListener('DOMContentLoaded', function () {
    const departmentCode = document.getElementById('departmentCode');
    if (!departmentCode) return; // Stop if not on this page

    const practicalSelect = document.getElementById('practicalLecturerSelect');
    const tutorialSelect = document.getElementById('tutorialLecturerSelect');

    departmentCode.addEventListener('change', function () {
        const deptValue = this.value;

        // Reset both selects to default placeholder
        practicalSelect.innerHTML = '<option value="" disabled selected>Select Practical Lecturer</option>';
        tutorialSelect.innerHTML = '<option value="" disabled selected>Select Tutorial Lecturer</option>';

        if (deptValue) {
            fetch(`/get_lecturers_by_department/${deptValue}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(lecturer => {
                        const practicalOption = document.createElement('option');
                        practicalOption.value = lecturer.userName;
                        practicalOption.textContent = lecturer.userName;
                        practicalSelect.appendChild(practicalOption);

                        const tutorialOption = document.createElement('option');
                        tutorialOption.value = lecturer.userName;
                        tutorialOption.textContent = lecturer.userName;
                        tutorialSelect.appendChild(tutorialOption);
                    });
                })
                .catch(error => console.error('Error fetching lecturers:', error));
        }
    });
});










