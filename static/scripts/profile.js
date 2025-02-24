document.addEventListener('DOMContentLoaded', function () {
    // Menu elements
    const menuProfile = document.getElementById('menu-profile');
    const menuEvents = document.getElementById('menu-events');

    // Section elements
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');

    // Set initial state based on authentication
    if (isAuthenticated) {
        menuProfile.textContent = "Profile";
        if (menuEvents) {
            menuEvents.style.display = "inline-block";
        }
        showSection('profile');  // Show profile section by default if authenticated
    } else {
        menuProfile.textContent = "Login";
        showSection('profile');  // Default view with login prompt
    }

    // Event Listener for Profile/Login Button
    menuProfile.addEventListener('click', () => {
        if (!isAuthenticated) {
            window.location.href = '/login';  // Redirect to /login if not authenticated
        } else {
            showSection('profile');  // Show profile section if authenticated
        }
    });

    // Event Listener for Events Button (if exists)
    if (menuEvents) {
        menuEvents.addEventListener('click', () => showSection('events'));
    }

    // --- Functions ---

    function showSection(section) {
        profileSection.classList.remove('active');
        menuProfile.classList.remove('active');
        if (menuEvents) menuEvents.classList.remove('active');

        if (section === 'profile') {
            profileSection.classList.add('active');
            menuProfile.classList.add('active');
        } else if (section === 'events' && eventsSection) {
            eventsSection.classList.add('active');
            if (menuEvents) menuEvents.classList.add('active');
        }
    }
});
