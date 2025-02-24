document.addEventListener('DOMContentLoaded', function () {
    // Menu elements
    const menuProfile = document.getElementById('menu-profile');
    const menuEvents = document.getElementById('menu-events');

    // Section elements
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');

    // Function to hide all sections and then show one
    function showSection(section) {
        if (profileSection) profileSection.style.display = 'none';
        if (eventsSection) eventsSection.style.display = 'none';
        
        if (section === 'profile' && profileSection) {
            profileSection.style.display = 'block';
        } else if (section === 'events' && eventsSection) {
            eventsSection.style.display = 'block';
        }
    }

    if (isAuthenticated) {
        // If authenticated, change the profile button text and attach event listeners
        menuProfile.textContent = "Profile";
        menuProfile.addEventListener('click', () => { showSection('profile'); });
        
        // Ensure events button is visible and attach its listener
        if (menuEvents) {
            menuEvents.style.display = "inline-block";
            menuEvents.addEventListener('click', () => { showSection('events'); });
        }
        // On load, show the profile section with the user's details
        showSection('profile');
    } else {
        // If not authenticated, the profile button acts as a login trigger
        menuProfile.textContent = "Login";
        menuProfile.addEventListener('click', () => { window.location.href = '/login'; });
        
        // Hide events button if it exists
        if (menuEvents) {
            menuEvents.style.display = "none";
        }
        // Optionally, you might choose to show a default prompt
        if (profileSection) {
            // The template already shows a login prompt message if not authenticated,
            // so you might just leave it visible.
            profileSection.style.display = 'block';
        }
    }
});
