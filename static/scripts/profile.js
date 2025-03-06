document.addEventListener('DOMContentLoaded', function () {
    // Section elements
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');
    const eventsContent = document.getElementById('events-section-content');
    const collectBtn = document.getElementById('collect-events-btn');
    const createEventBtn = document.getElementById('create-event-btn');
    const renewSection = document.getElementById('renew-section');
    
    // Utility: Get URL parameters (if needed)
    function getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // Function to hide all sections and show one
    function showSection(section) {
        if (profileSection) profileSection.style.display = 'none';
        if (eventsSection) eventsSection.style.display = 'none';
        if (renewSection) renewSection.style.display = 'none';
        
        if (section === 'profile' && profileSection) {
            profileSection.style.display = 'block';
        } else if (section === 'events' && eventsSection) {
            eventsSection.style.display = 'block';
        } else if (section === 'renew' && renewSection) {
            renewSection.style.display = 'block';
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
                        if (event.cover && event.cover.source && event.cover.source.trim() !== '') {
                            coverHtml = `<img src="${event.cover.source}" alt="Event Cover" class="event-cover">`;
                        }

                        // Only build the Facebook link if the event ID does NOT start with "OJC"
                        let facebookLinkHtml = '';
                        if (!event.id.startsWith("OJC")) {
                            facebookLinkHtml = `<p><a href="https://www.facebook.com/events/${event.id}" target="_blank">View on Facebook</a></p>`;
                        }
                    
                        eventDiv.innerHTML = `
                            ${coverHtml}
                            <h3>${event.name}</h3>
                            <p><strong>Start:</strong> ${startDate}</p>
                            <p>${event.description}</p>
                            <p><strong>Location:</strong> ${event.place ? event.place.name : 'N/A'}</p>
                            ${ (!event.id.startsWith("OJC") ? `<p><a href="https://www.facebook.com/events/${event.id}" target="_blank">View on Facebook</a></p>` : '') }
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
        const menuRenew = document.getElementById('renewButton');
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
        if (menuRenew) {
            menuRenew.style.display = "inline-block";
            menuRenew.addEventListener('click', () => { 
                showSection('renew');
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
        const joinButton = document.getElementById('join-button');
        menuLogin.addEventListener('click', () => { window.location.href = '/login'; });
        if (joinButton) {
            joinButton.addEventListener('click', () => { 
                // Hide the default prompt and show the join section
                const defaultPrompt = document.getElementById('default-prompt');
                if (defaultPrompt) defaultPrompt.style.display = 'none';
                const joinSection = document.getElementById('join-section');
                joinSection.style.display = 'block';
            });
        }
    }

    // Set up the "Collect" button listener to trigger the sync process
    if (collectBtn) {
        collectBtn.addEventListener('click', () => {
            document.getElementById('collect-events-btn').addEventListener('click', function() {
              window.location.href = '/sync-public-events';
            });
        });
    }

    // Set up the "Create Event" button listener to trigger the sync process
    if (createEventBtn) {
        createEventBtn.addEventListener('click', () => {
            document.getElementById('create-event-btn').addEventListener('click', function() {
              window.location.href = '/create_event';
            });
        });
    }
});
