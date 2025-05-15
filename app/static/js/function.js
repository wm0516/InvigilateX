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


document.addEventListener('DOMContentLoaded', function() {
    const tabLinks = document.querySelectorAll('.tab-link');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            const tabId = this.getAttribute('data-tab');
            
            // If the link has NO href (should stay on same page)
            if (!href) {
                e.preventDefault(); // Prevent navigation
                switchTab(tabId);   // Switch tab content
            }
            // Otherwise, let the browser handle navigation normally
        });
    });

    // Function to handle tab switching
    function switchTab(tabId) {
        // Remove active class from all tabs and panes
        document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding pane
        const activeTab = document.querySelector(`.tab-link[data-tab="${tabId}"]`);
        const activePane = document.getElementById(tabId);
        
        if (activeTab) activeTab.classList.add('active');
        if (activePane) activePane.classList.add('active');
    }
});