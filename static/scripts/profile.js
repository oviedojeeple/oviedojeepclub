document.addEventListener('DOMContentLoaded', function () {
    // Section elements
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');
    const eventsContent = document.getElementById('events-section-content');
    const collectBtn = document.getElementById('collect-events-btn');

    // Utility: Get URL parameters (if needed)
    function getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // Function to hide all sections and show one
    function showSection(section) {
        if (profileSection) profileSection.style.display = 'none';
        if (eventsSection) eventsSection.style.display = 'none';
        
        if (section === 'profile' && profileSection) {
            profileSection.style.display = 'block';
        } else if (section === 'events' && eventsSection) {
            eventsSection.style.display = 'block';
        }
    }

    // Function to load events from the blob
    function loadBlobEvents() {
        fetch('/blob-events')
            .then(response => response.json())
            .then(data => {
                eventsContent.innerHTML = '';
                if (data.error) {
                    eventsContent.innerHTML = `<p>Error: ${data.error}</p>`;
                    return;
                }
                if (data.length === 0) {
                    eventsContent.innerHTML = '<p>No events found.</p>';
                } else {
                    data.forEach(event => {
                        const eventDiv = document.createElement('div');
                        eventDiv.classList.add('event');
                        const startDate = new Date(event.start_time).toLocaleString();

                        // Include cover image if available
                        let coverHtml = '';
                        if (event.cover && event.cover.source) {
                            coverHtml = `<img src="${event.cover.source}" alt="Event Cover" class="event-cover">`;
                        }

                        eventDiv.innerHTML = `
                            ${coverHtml}
                            <h3>${event.name}</h3>
                            <p><strong>Start:</strong> ${startDate}</p>
                            <p>${event.description}</p>
                            <p><strong>Location:</strong> ${event.place ? event.place.name : 'N/A'}</p>
                            <p><a href="https://www.facebook.com/events/${event.id}" target="_blank">View on Facebook</a></p>
                        `;
                        eventsContent.appendChild(eventDiv);
                    });
                }
            })
            .catch(error => {
                console.error("Error loading blob events", error);
                eventsContent.innerHTML = '<p>Error loading events.</p>';
            });
    }

    // Set up menu button listeners
    if (isAuthenticated) {
        const menuProfile = document.getElementById('menu-profile');
        const menuEvents = document.getElementById('menu-events');
        const menuMerch = document.getElementById('menu-merchandise');
        const menuLogout = document.getElementById('menu-logout');
        
        menuProfile.addEventListener('click', () => { 
            showSection('profile'); 
        });
        if (menuEvents) {
            menuEvents.style.display = "inline-block";
            menuEvents.addEventListener('click', () => { 
                showSection('events');
                loadBlobEvents();
            });
        }
        if (menuMerch) {
            menuMerch.addEventListener('click', () => {
                window.open('https://goinkit.com/oviedo_jeep_club/shop/home', '_blank');
            });
        }
        if (menuLogout) {
            menuLogout.addEventListener('click', () => {
                window.location.href = '/logout';
            });
        }
        
        // Check if URL has section=events; if so, load events
        const sectionParam = getQueryParam("section");
        if (sectionParam === "events") {
            history.replaceState(null, "", window.location.pathname);
            showSection('events');
            loadBlobEvents();
        } else {
            showSection('profile');
        }
    } else {
        const menuLogin = document.getElementById('menu-login');
        const menuJoin = document.getElementById('menu-join');
        menuLogin.addEventListener('click', () => { window.location.href = '/login'; });
        menuJoin.addEventListener('click', () => { window.location.href = '/pay'; });
    }

    // Set up the "Collect" button listener to trigger the sync process
    if (collectBtn) {
        collectBtn.addEventListener('click', () => {
            fetch('/sync-public-events')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert("Error syncing events: " + data.error);
                    } else {
                        alert(data.message);
                        // Reload events from blob after sync
                        loadBlobEvents();
                    }
                })
                .catch(error => {
                    console.error("Error syncing events", error);
                    alert("Error syncing events.");
                });
        });
    }
});
