document.addEventListener('DOMContentLoaded', function () {
    // Get menu elements
    const menuProfile = document.getElementById('menu-profile');
    const menuEvents = document.getElementById('menu-events');

    // Get section elements (if they exist)
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');
    
    // If not authenticated, clicking the profile button should trigger login
    if (!isAuthenticated) {
        menuProfile.addEventListener('click', () => {
            window.location.href = '/login';
        });
    } else {
        // If authenticated, update button text and attach listeners
        menuProfile.textContent = "Profile";
        menuProfile.addEventListener('click', () => {
            showSection('profile');
        });
        
        if (menuEvents) {
            menuEvents.addEventListener('click', () => {
                showSection('events');
            });
        }
    }

    // --- Function to show sections ---
    function showSection(section) {
        // Hide both sections if they exist
        if (profileSection) profileSection.classList.remove('active');
        if (eventsSection) eventsSection.classList.remove('active');
        
        // Show the requested section
        if (section === 'profile' && profileSection) {
            profileSection.classList.add('active');
        } else if (section === 'events' && eventsSection) {
            eventsSection.classList.add('active');
        }
    }
});
