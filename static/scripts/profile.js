document.addEventListener('DOMContentLoaded', function () {
    // Utility: Get URL parameters
    function getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // Section elements (Profile and Events already exist)
    const profileSection = document.getElementById('profile-section');
    const eventsSection = document.getElementById('events-section');
    const eventsContent = document.getElementById('events-section-content');

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

    // Function to load and display Facebook events
    function loadEvents() {
        fetch('/fb-events')
          .then(response => response.json())
          .then(data => {
              // Sort events by start_time (ascending order here, adjust if needed)
              data.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

              // Clear previous content
              eventsContent.innerHTML = '';

              if (data.length === 0) {
                  eventsContent.innerHTML = '<p>No events found.</p>';
              } else {
                  data.forEach(event => {
                    const eventDiv = document.createElement('div');
                    eventDiv.classList.add('event');
                    const startDate = new Date(event.start_time).toLocaleString();
                
                    // Check if a cover image exists
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
              console.error("Error loading events", error);
              eventsContent.innerHTML = '<p>Error loading events.</p>';
          });
    }

    // Your existing button setup...
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
                // If no Facebook token exists, start the OAuth flow.
                if (!fbAccessToken) {
                    window.location.href = "/facebook/login";
                } else {
                    showSection('events');
                    loadEvents();
                }
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
        
        // Check URL for section parameter and auto-load if needed:
        const sectionParam = getQueryParam("section");
        if (sectionParam === "events") {
            // Optionally clear the query parameters from the URL
            history.replaceState(null, "", window.location.pathname);
            showSection('events');
            loadEvents();
        } else {
            // Default to profile section
            showSection('profile');
        }
    } else {
        const menuLogin = document.getElementById('menu-login');
        const menuJoin = document.getElementById('menu-join');
        
        menuLogin.addEventListener('click', () => { window.location.href = '/login'; });
        menuJoin.addEventListener('click', () => { window.location.href = '/pay'; });
    }
});
