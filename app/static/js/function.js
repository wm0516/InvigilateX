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










// Function to track the selected date to display out the date in manageExam
document.addEventListener("DOMContentLoaded", function () {
    const examDateInput = document.getElementById('examDate');
    const examDayInput = document.getElementById('examDay');

    // Format date to YYYY-MM-DD
    const formatDate = (date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const today = new Date();
    const minDate = formatDate(today);

    // Set max date to exactly 1 year later (same date next year)
    const nextYearSameDay = new Date(today);
    nextYearSameDay.setFullYear(today.getFullYear() + 1);
    const maxDate = formatDate(nextYearSameDay);

    // Apply min/max restrictions
    examDateInput.min = minDate;
    examDateInput.max = maxDate;

    // Handle date selection
    examDateInput.addEventListener('change', function () {
        const selectedDate = new Date(this.value);
        const day = selectedDate.getDay(); // 0 = Sunday, 6 = Saturday

        // Check if selected date is within range
        const selected = formatDate(selectedDate);
        if (selected < minDate || selected > maxDate) {
            alert("Date must be within one year from today.");
            this.value = '';
            examDayInput.value = '';
            return;
        }

        // Disallow weekends
        /*if (day === 0 || day === 6) {
            alert("Weekends are not allowed.");
            this.value = '';
            examDayInput.value = '';
            return;
        }*/

        const days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
        examDayInput.value = days[day];
    });
});

document.getElementById('endTime').addEventListener('change', function() {
  const start = document.getElementById('startTime').value;
  const end = this.value;
  if (end <= start) {
    alert('End time must be later than start time');
    this.value = '';
  }
});





// Function for second navigation tab
function showSection(sectionId, event) {
    event.preventDefault();

    // Hide forms only if they exist
    ["announceForm", "uploadForm", "manualForm"].forEach(formId => {
        const form = document.getElementById(formId);
        if (form) form.style.display = "none";
    });

    // Show selected form if it exists
    const selectedForm = document.getElementById(sectionId.replace("Section", "Form"));
    if (selectedForm) selectedForm.style.display = "block";

    // Tab highlight (limit to second navigation container)
    document.querySelectorAll(".second-nav .tab-link").forEach(tab => tab.classList.remove("active"));
    event.currentTarget.classList.add("active");

    // Save current tab to localStorage
    localStorage.setItem("activeSecondTab", sectionId);
}

// Restore second tab state on page load
document.addEventListener("DOMContentLoaded", function () {
    let savedSecondTab = localStorage.getItem("activeSecondTab");

    // Hide all forms first
    ["announceForm", "uploadForm", "manualForm"].forEach(formId => {
        const form = document.getElementById(formId);
        if (form) form.style.display = "none";
    });

    // If saved tab doesn't exist, fallback to first available
    if (!document.getElementById(savedSecondTab?.replace("Section", "Form"))) {
        const firstAvailableTab = document.querySelector(".second-nav .tab-link");
        if (firstAvailableTab) {
            savedSecondTab = firstAvailableTab.getAttribute("data-section");
        }
    }

    if (savedSecondTab) {
        // Highlight the saved tab
        document.querySelectorAll(".second-nav .tab-link").forEach(tab => {
            if (tab.getAttribute("data-section") === savedSecondTab) {
                tab.classList.add("active");
            }
        });

        // Show the correct form
        const savedForm = document.getElementById(savedSecondTab.replace("Section", "Form"));
        if (savedForm) savedForm.style.display = "block";
    }
});










// Function for after getting department code, related course code will be displayed out in Manage Exam page
document.getElementById('programCode').addEventListener('change', function() {
    let deptCode = this.value;
    let courseSectionSelect = document.getElementById('courseSection');
    let practicalLecturerSelect = document.getElementById('practicalLecturer');
    let tutorialLecturerSelect = document.getElementById('tutorialLecturer');
    let studentSelect = document.getElementById('student');
    
    // Reset the course section dropdown
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


// Function for after getting course code, practical, tutorial, and number of students will be displayed out in Manage Exam page
document.getElementById('courseSection').addEventListener('change', function() {
    let deptCode = document.getElementById('programCode').value;
    let sectionCode = document.getElementById('courseSection').value;
    console.log("Selected:", deptCode, sectionCode); // Debug

    if (deptCode && sectionCode) {
        fetch(`/get_course_details/${deptCode}/${encodeURIComponent(sectionCode)}`)  // ✅ FIXED HERE
            .then(response => {
                if (!response.ok) throw new Error("API failed");
                return response.json();
            })
            .then(data => {
                console.log("API Data:", data); // Debug response
                document.getElementById('practicalLecturer').value = data.practicalLecturer || "";
                document.getElementById('tutorialLecturer').value = data.tutorialLecturer || "";
                document.getElementById('student').value = data.student || "";
            })
            .catch(err => console.error("Error:", err));
    }
});



// When department code changes, fetch lecturers for that department
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('departmentCode').addEventListener('change', function () {
        const deptValue = this.value;
        const practicalSelect = document.getElementById('practicalLecturerSelect');
        const tutorialSelect = document.getElementById('tutorialLecturerSelect');

        // Reset both selects to default
        practicalSelect.innerHTML = '<option value="" disabled selected>Select Practical Lecturer</option>';
        tutorialSelect.innerHTML = '<option value="" disabled selected>Select Tutorial Lecturer</option>';

        if (deptValue) {
            fetch(`/get_lecturers_by_department/${deptValue}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(lecturer => {
                        let practicalOption = document.createElement('option');
                        practicalOption.value = lecturer.userName;
                        practicalOption.textContent = lecturer.userName;
                        practicalSelect.appendChild(practicalOption);

                        let tutorialOption = document.createElement('option');
                        tutorialOption.value = lecturer.userName;
                        tutorialOption.textContent = lecturer.userName;
                        tutorialSelect.appendChild(tutorialOption);
                    });


                })
                .catch(error => console.error('Error fetching lecturers:', error));
        }
    });
}
















// Function to trigger search when any field changes
function triggerSearch() {
    const selects = [
        document.getElementById('courseDepartment'),
        document.getElementById('courseCodeSection'),
        document.getElementById('courseName')
    ];

    // Get selected values
    const values = selects.map(s => s.value.trim());
    const selectedCount = values.filter(v => v !== '').length;

    if (selectedCount === 0) {
        selects.forEach(s => s.disabled = false);
        clearCourseInputs();
        return;
    }

    if (selectedCount > 1) {
        alert('Please select only one search criteria at a time.');
        selects.forEach(s => {
            s.value = '';
            s.disabled = false;
        });
        clearCourseInputs();
        return;
    }

    // Disable unselected selects
    selects.forEach((s, i) => {
        s.disabled = (values[i] === '') ? false : true;
    });

    // Prepare data object for fetch
    const data = {
        department: values[0],
        codeSection: values[1],
        courseName: values[2]
    };

    fetch('/search_course', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(course => {
        if (course.error) {
            alert(course.error);
            clearCourseInputs();
            return;
        }

        // Fill inputs and selects with course data
        document.querySelector('input[name="courseSection"]').value = course.courseSection || '';
        document.querySelector('input[name="courseCode"]').value = course.courseCode || '';
        document.querySelector('input[name="courseHour"]').value = course.courseHour || '';
        document.querySelector('input[name="courseStudent"]').value = course.courseStudent || '';
        document.querySelector('input[name="coursePractical"]').value = course.coursePractical || '';
        document.querySelector('input[name="courseTutorial"]').value = course.courseTutorial || '';

        selects[0].value = course.courseDepartment || '';
        selects[1].value = course.courseCodeSection || '';
        selects[2].value = course.courseName || '';
    })
    .catch(err => console.error('Fetch error:', err));
}

function clearCourseInputs() {
    ['courseSection', 'courseCode', 'courseHour', 'courseStudent', 'coursePractical', 'courseTutorial']
    .forEach(name => {
        const input = document.querySelector(`input[name="${name}"]`);
        if (input) input.value = '';
    });
}

// Attach event listeners
['courseDepartment', 'courseCodeSection', 'courseName'].forEach(id => {
    document.getElementById(id).addEventListener('change', triggerSearch);
});
