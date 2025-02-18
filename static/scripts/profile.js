document.addEventListener('DOMContentLoaded', function () {
  // Global variable to hold the authenticated user profile
  let userProfile = null;

  // Menu elements
  const menuProfile = document.getElementById('menu-profile');
  const menuEvents = document.getElementById('menu-events');

  // Section elements
  const profileSection = document.getElementById('profile-section');
  const eventsSection = document.getElementById('events-section');

  // Set default view: Profile button initially reads "Login"
  showSection('profile');
  menuProfile.textContent = "Login";

  // Event Listeners for Menu Buttons
  menuProfile.addEventListener('click', async () => {
      if (!userProfile) {
          menuProfile.textContent = "Signing in...";
          await authenticateWithJeeple();
          if (userProfile) {
              menuProfile.textContent = "Profile";
              if (menuEvents) {
                  menuEvents.style.display = "inline-block";
              }
              showSection('profile');
          } else {
              menuProfile.textContent = "Login";
          }
      }
  });

  if (menuEvents) {
      menuEvents.addEventListener('click', () => showSection('events'));
  }

  // --- Functions ---

  function showSection(section) {
      profileSection.classList.remove('active');
      menuProfile.classList.remove('active');
      menuEvents.classList.remove('active');

      if (section === 'profile') {
          profileSection.classList.add('active');
          menuProfile.classList.add('active');
      } else if (section === 'events') {
          eventsSection.classList.add('active');
          menuEvents.classList.add('active');
      }
  } // <-- Now properly closed

  async function authenticateWithJeeple() {
      if (!window) {
          console.error("Jeeple authentication not available.");
          return;
      }
      try {
          const jeepleUser = window.userProfile; // Removed `await`
          if (!jeepleUser) {
              console.error("No user profile found.");
              return;
          }

          console.log("Authenticated Jeeple User:", jeepleUser);
          localStorage.setItem('jeepleUser', JSON.stringify(jeepleUser));

          const email = jeepleUser?.email || "";
          if (!email) {
              console.error("Email not found.");
              return;
          }

          const response = await fetch('/fetch-profile', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email })
          });
          const validationResult = await response.json();

          if (validationResult.content) {
              userProfile = validationResult;
              console.log("Profile validated:", userProfile.content.name);
              displayProfile(userProfile);
          } else {
              console.error("Profile validation failed or content is missing:", validationResult);
          }
      } catch (error) {
          console.error("An error occurred during authentication:", error);
      }
  }

  function displayProfile(profileData) {
      const profileContainer = document.getElementById('profile-container');
      profileContainer.innerHTML = '';
      if (profileData.content) {
          const content = profileData.content;
          const detailsTable = document.createElement('table');
          detailsTable.classList.add('profile-details');
          const details = [
              { label: 'Name', value: content.name },
              { label: 'Email', value: content.email }
          ];
          details.forEach(detail => {
              if (detail.value) {
                  const row = document.createElement('tr');
                  const labelCell = document.createElement('td');
                  labelCell.textContent = detail.label;
                  const valueCell = document.createElement('td');
                  valueCell.textContent = detail.value; // <-- Fixed missing assignment
                  row.appendChild(labelCell);
                  row.appendChild(valueCell);
                  detailsTable.appendChild(row);
              }
          });
          profileContainer.appendChild(detailsTable);
      } else {
          profileContainer.innerHTML = "<p class='empty-profile'>No profile data available.</p>";
      }
  }
});
