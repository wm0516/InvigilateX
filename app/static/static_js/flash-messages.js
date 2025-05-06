/*function displayFlashMessages(containerId = 'flash-messages', timeout = 5000) {
    if (typeof flashMessages === 'undefined') {
        console.warn("No flashMessages defined");
        return;
    }

    const container = document.getElementById(containerId);

    if (!container) {
        console.warn(`Flash message container with ID '${containerId}' not found`);
        return;
    }

    flashMessages.forEach(([category, message]) => {
        const div = document.createElement('div');
        div.className = `flash-message flash-${category}`;
        div.textContent = message;
        container.appendChild(div);

        // Auto-remove after timeout
        setTimeout(() => div.remove(), timeout);
    });
}

document.addEventListener('DOMContentLoaded', function () {
    displayFlashMessages();
});
*/