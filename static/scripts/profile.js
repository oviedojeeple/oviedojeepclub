document.addEventListener('DOMContentLoaded', function () {
    // Section elements (Profile and Events already exist)
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
        // Authenticated buttons
        const menuProfile = document.getElementById('menu-profile');
        const menuEvents = document.getElementById('menu-events');
        const menuMerch = document.getElementById('menu-merchandise');
        const menuLogout = document.getElementById('menu-logout');
        
        // Set up listeners for Profile and Events as before
        menuProfile.addEventListener('click', () => { showSection('profile'); });
        if (menuEvents) {
            menuEvents.style.display = "inline-block";
            menuEvents.addEventListener('click', () => { showSection('events'); });
        }
        // Add Merchandise: open store in a new tab
        if (menuMerch) {
            menuMerch.addEventListener('click', () => {
                window.open('https://goinkit.com/oviedo_jeep_club/shop/home', '_blank');
            });
        }
        // Add Logout: redirect to /logout
        if (menuLogout) {
            menuLogout.addEventListener('click', () => {
                window.location.href = '/logout';
            });
        }
        // Show the profile section on load
        showSection('profile');
    } else {
        // Non-authenticated buttons
        const menuLogin = document.getElementById('menu-login');
        const menuJoin = document.getElementById('menu-join');
        
        // Login button goes to /login
        menuLogin.addEventListener('click', () => { window.location.href = '/login'; });
        // Join button goes to /pay (membership fee page)
        menuJoin.addEventListener('click', () => { window.location.href = '/pay'; });
        
        // Optionally, you can choose what section to display by default here
    }
});
