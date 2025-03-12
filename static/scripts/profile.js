document.addEventListener('DOMContentLoaded', function () {
    // Section elements
    const profileSection = document.getElementById('profile-section');
    const familySection = document.getElementById('family-section');
    const eventsSection = document.getElementById('events-section');
    const eventsContent = document.getElementById('events-section-content');
    const collectBtn = document.getElementById('collect-events-btn');
    const createEventBtn = document.getElementById('create-event-btn');
    const listOldEventsBtn = document.getElementById('list-oldevents-btn');
    const renewSection = document.getElementById('renew-section');
    
    // Utility: Get URL parameters (if needed)
    function getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // Function to hide all sections and show one
    function showSection(section) {
        if (profileSection) profileSection.style.display = 'none';
        if (familySection) familySection.style.display = 'none';
        if (eventsSection) eventsSection.style.display = 'none';
        if (renewSection) renewSection.style.display = 'none';
        
        if (section === 'profile' && profileSection) {
            if (profileSection) profileSection.style.display = 'block';
            if (familySection) familySection.style.display = 'block';
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
                        
                        // Only show a delete button if the event is custom (ID starts with OJC)
                        let deleteButtonHtml = '';
                        if (event.id.startsWith("OJC") && userJobTitle === 'OJC Board Member') {
                            deleteButtonHtml = `<button class="delete-event-btn" data-event-id="${event.id}">Delete</button>`;
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
                            ${deleteButtonHtml}
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

    // Function to load old events from the blob
    function loadOldEvents() {
        fetch('/list_old_events', { method: 'GET' }) // Force GET request
            .then(response => response.json())
            .then(data => {
                eventsContent.innerHTML = ''; // Clear existing events
        
                if (data.error) {
                    console.error("Error loading old events:", data.error);
                    eventsContent.innerHTML = `<p>Error: ${data.error}</p>`;
                    return;
                }
    
                if (data.events.length === 0) {
                    eventsContent.innerHTML = '<p>No past events found.</p>';
                } else {
                    data.events.forEach(event => {
                        const eventDiv = document.createElement('div');
                        eventDiv.classList.add('event');
                        const startDate = new Date(event.start_time).toLocaleString();
    
                        // Include cover image if available
                        let coverHtml = '';
                        if (event.cover && event.cover.source && event.cover.source.trim() !== '') {
                            coverHtml = `<img src="${event.cover.source}" alt="Event Cover" class="event-cover">`;
                        }
    
                        // Show delete button for custom events (if applicable)
                        let deleteButtonHtml = '';
                        if (event.id.startsWith("OJC") && userJobTitle === 'OJC Board Member') {
                            deleteButtonHtml = `<button class="delete-event-btn" data-event-id="${event.id}">Delete</button>`;
                        }
    
                        // Build the Facebook link only if the event ID does NOT start with "OJC"
                        let facebookLinkHtml = '';
                        if (!event.id.startsWith("OJC")) {
                            facebookLinkHtml = `<p><a href="https://www.facebook.com/events/${event.id}" target="_blank">View on Facebook</a></p>`;
                        }
    
                        // Construct event HTML
                        eventDiv.innerHTML = `
                            ${coverHtml}
                            <h3>${event.name}</h3>
                            <p><strong>Start:</strong> ${startDate}</p>
                            <p>${event.description}</p>
                            <p><strong>Location:</strong> ${event.place ? event.place.name : 'N/A'}</p>
                            ${facebookLinkHtml}
                            ${deleteButtonHtml}
                        `;
                        eventsContent.appendChild(eventDiv);
                    });
                }
            })
            .catch(error => {
                console.error("Error loading old events:", error);
                eventsContent.innerHTML = '<p>Error loading old events.</p>';
            });
    }
    
    // Attach event delegation for delete buttons on the events container.
    if (eventsContent) {
        eventsContent.addEventListener('click', function(e) {
            if (e.target && e.target.classList.contains('delete-event-btn')) {
                const eventId = e.target.getAttribute('data-event-id');
                if (confirm("Are you sure you want to delete this event?")) {
                    fetch(`/delete_event/${eventId}`, { method: 'POST' })
                        .then(response => {
                            if (response.ok) {
                                loadOldEvents(); // Reload events after deletion
                            } else {
                                alert("Error deleting event.");
                            }
                        })
                        .catch(error => {
                            console.error("Error deleting event:", error);
                            alert("Error deleting event.");
                        });
                }
            }
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

        // Set up the "List Old Events" button listener
        if (listOldEventsBtn) {
            listOldEventsBtn.addEventListener('click', function() {
                showSection('events');
                loadOldEvents(); // Load old events on click
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

    // Set up the "Collect" button listener
    if (collectBtn) {
        collectBtn.addEventListener('click', function() {
            window.location.href = '/sync-public-events';
        });
    }
    
    // Set up the "Create Event" button listener
    if (createEventBtn) {
        createEventBtn.addEventListener('click', function() {
            window.location.href = '/create_event';
        });
    }

    // Set up the "List Old Events" button listener
    if (listOldEventsBtn) {
        listOldEventsBtn.addEventListener('click', function() {
            showSection('events');
            loadOldEvents(); // Load old events on click
        });
    }
    
  // Family Member functionality: check for an existing family member and handle invite submission
  // Family Member Section Elements
  const familyMemberInfo = document.getElementById('family-member-info');
  const familyMemberName = document.getElementById('family-member-name');
  const familyMemberEmail = document.getElementById('family-member-email');
  const familyInviteForm = document.getElementById('family-invite-form');
  const sendFamilyInviteBtn = document.getElementById('send-family-invite-btn');

  // Check if the user is authenticated before trying to load family info
  if (isAuthenticated) {
    // Query your back end for family members associated with the current membership number
    fetch('/family-members')
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          console.error("Error fetching family member:", data.error);
          return;
        }
        if (data.length > 0) {
          // If a family member exists, display their details (assuming one for now)
          familyMemberName.innerText = "Name: " + data[0].displayName;
          // Use the email from the Graph API response (adjust if needed)
          familyMemberEmail.innerText = "Email: " + data[0].mailNickname.replace("_at_", "@");
          familyMemberInfo.style.display = "block";
          familyInviteForm.style.display = "none";
        } else {
          // No family member exists: show the invite form
          familyInviteForm.style.display = "block";
          familyMemberInfo.style.display = "none";
        }
      })
      .catch(error => {
        console.error("Error:", error);
      });

    // Handle invite submission when the "Send Invite" button is clicked
    if (sendFamilyInviteBtn) {
      sendFamilyInviteBtn.addEventListener("click", function() {
        const familyNameValue = document.getElementById("family_name").value;
        const familyEmailValue = document.getElementById("family_email").value;
        if (!familyNameValue || !familyEmailValue) {
          alert("Please fill out both the family member's name and email.");
          return;
        }
        // Prepare form data for the POST request
        const formData = new URLSearchParams();
        formData.append("family_name", familyNameValue);
        formData.append("family_email", familyEmailValue);

        fetch('/invite_family', {
          method: 'POST',
          body: formData,
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            alert("Error: " + data.error);
          } else {
            alert("Invitation sent successfully!");
            // Optionally hide the invite form after sending
            familyInviteForm.style.display = "none";
          }
        })
        .catch(err => {
          console.error("Error sending invitation:", err);
        });
      });
    }
  }
});
