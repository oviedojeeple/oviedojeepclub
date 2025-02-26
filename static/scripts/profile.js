document.addEventListener('DOMContentLoaded', function () {
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
              // Sort events by start_time (ascending)
              data.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

              // Clear previous content
              eventsContent.innerHTML = '';

              if (data.length === 0) {
                  eventsContent.innerHTML = '<p>No events found.</p>';
              } else {
                  data.forEach(event => {
                      // Create a container for each event
                      const eventDiv = document.createElement('div');
                      eventDiv.classList.add('event');

                      // Format the start date nicely
                      const startDate = new Date(event.start_time).toLocaleString();

                      // Populate event details
                      eventDiv.innerHTML = `
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

    if (isAuthenticated) {
        // Authenticated buttons
        const menuProfile = document.getElementById('menu-profile');
        const menuEvents = document.getElementById('menu-events');
        const menuMerch = document.getElementById('menu-merchandise');
        const menuLogout = document.getElementById('menu-logout');
        
        // Set up listeners for Profile and Events
        menuProfile.addEventListener('click', () => { 
            showSection('profile'); 
        });
        if (menuEvents) {
            menuEvents.style.display = "inline-block";
            menuEvents.addEventListener('click', () => { 
                showSection('events'); 
                loadEvents();
            });
        }
        // Merchandise: open store in a new tab
        if (menuMerch) {
            menuMerch.addEventListener('click', () => {
                window.open('https://goinkit.com/oviedo_jeep_club/shop/home', '_blank');
            });
        }
        // Logout: redirect to /logout
        if (menuLogout) {
            menuLogout.addEventListener('click', () => {
                window.location.href = '/logout';
            });
        }
        // Show the profile section on initial load
        showSection('profile');
    } else {
        // Non-authenticated buttons
        const menuLogin = document.getElementById('menu-login');
        const menuJoin = document.getElementById('menu-join');
        
        // Login button goes to /login
        menuLogin.addEventListener('click', () => { 
            window.location.href = '/login'; 
        });
        // Join button goes to /pay (membership fee page)
        menuJoin.addEventListener('click', () => { 
            window.location.href = '/pay'; 
        });
    }
});
