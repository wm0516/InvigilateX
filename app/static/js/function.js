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



// Admin Manage Exam Page(Manual): Function to Read Selected "Department Code" and related "Course Code" will be displayed out
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


// Admin Manage Exam Page(Manual): Function to Read Selected "Course Code Section" and related "Total of Students, Practical and Tutorial Lecturer" will be displayed out
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


// Admin Manage Course Page(Manual): Function to Read Selected "Department Code" and related "Lecturer" will be displayed out
document.addEventListener('DOMContentLoaded', function () {
    const departmentCode = document.getElementById('departmentCode');
    if (!departmentCode) return; // Stop if not on this page

    const practicalSelect = document.getElementById('practicalLecturerSelect');
    const tutorialSelect = document.getElementById('tutorialLecturerSelect');

    departmentCode.addEventListener('change', function () {
        const deptValue = this.value;
        console.log("Selected Department Code is:", deptValue);

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


document.addEventListener("DOMContentLoaded", function () {
    const courseSelect = document.getElementById("editCourseSelect");
    const departmentSelect = document.getElementById('editDepartment');
    const courseCodeInput = document.getElementById('editCourseCode');
    const courseSectionInput = document.getElementById('editCourseSection');
    const courseNameInput = document.getElementById('editCourseName');
    const practicalSelect = document.getElementById('editPracticalLecturer');
    const tutorialSelect = document.getElementById('editTutorialLecturer');
    const courseHourInput = document.getElementById('editCourseHour');
    const courseStudentInput = document.getElementById('editCourseStudents');

    function populateLecturers(deptCode, selectedPractical, selectedTutorial) {
        if (!deptCode) {
            // If department is null/empty, keep existing lecturers
            practicalSelect.innerHTML = '';
            tutorialSelect.innerHTML = '';
            if (selectedPractical) {
                practicalSelect.innerHTML = `<option value="${selectedPractical}" selected>${selectedPractical}</option>`;
            }
            if (selectedTutorial) {
                tutorialSelect.innerHTML = `<option value="${selectedTutorial}" selected>${selectedTutorial}</option>`;
            }
            return;
        }

        fetch(`/get_lecturers_by_department/${encodeURIComponent(deptCode)}`)
            .then(resp => resp.json())
            .then(lecturers => {
                practicalSelect.innerHTML = '<option value="" disabled>Select Practical Lecturer</option>';
                tutorialSelect.innerHTML = '<option value="" disabled>Select Tutorial Lecturer</option>';

                lecturers.forEach(lecturer => {
                    const username = lecturer.userName.trim();

                    const practicalOption = document.createElement('option');
                    practicalOption.value = username;
                    practicalOption.textContent = username;
                    if (username.toLowerCase() === (selectedPractical || '').toLowerCase()) practicalOption.selected = true;
                    practicalSelect.appendChild(practicalOption);

                    const tutorialOption = document.createElement('option');
                    tutorialOption.value = username;
                    tutorialOption.textContent = username;
                    if (username.toLowerCase() === (selectedTutorial || '').toLowerCase()) tutorialOption.selected = true;
                    tutorialSelect.appendChild(tutorialOption);
                });
            })
            .catch(err => console.error('Error fetching lecturers:', err));
    }

    // --- When course is selected ---
    courseSelect.addEventListener('change', function () {
        const selectedCodeSection = this.value;
        if (!selectedCodeSection) return;

        fetch(`/get_courseCodeSection/${encodeURIComponent(selectedCodeSection)}`)
            .then(resp => resp.json())
            .then(course => {
                if (course.error) {
                    alert(course.error);
                    return;
                }

                departmentSelect.value = course.courseDepartment || '';
                courseCodeInput.value = course.courseCode;
                courseSectionInput.value = course.courseSection;
                courseNameInput.value = course.courseName;
                courseHourInput.value = course.courseHour;
                courseStudentInput.value = course.courseStudent;

                // Populate lecturers (even if department is null)
                populateLecturers(course.courseDepartment, course.coursePractical, course.courseTutorial);
            })
            .catch(err => console.error('Error fetching course:', err));
    });

    // --- When department changes manually ---
    departmentSelect.addEventListener('change', function () {
        const deptCode = this.value;
        populateLecturers(deptCode, null, null); // reset selection when department changes
    });
});














