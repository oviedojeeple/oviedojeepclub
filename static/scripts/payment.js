document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, 'sandbox');
    const card = await payments.card();
    await card.attach('#card-container');

    // Helper function to display flash messages
    function displayClientFlash(message, category = 'danger') {
        const container = document.getElementById('flash-messages');
        container.innerHTML = `<div class="flash-message flash-${category}">${message}</div>`;
    }

    // Handle Payment Form Submission
    document.querySelector('#payment-form').addEventListener('submit', async function (event) {
        event.preventDefault();
        
        // Retrieve user input values
        const email = document.getElementById('email').value;
        const displayName = document.getElementById('displayName').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Basic client-side check: ensure password and confirmation match.
        if (password !== confirmPassword) {
            displayClientFlash("Passwords do not match. Please re-enter.", "danger");
            return;
        }
        
        // Optionally, you could also validate the password using JavaScript regex,
        // but the HTML pattern attribute should enforce it in supporting browsers.
        const result = await card.tokenize();
        if (result.status === 'OK') {
            document.querySelector('#card-nonce').value = result.token;
            this.submit(); // Submit the form to /pay
        } else {
            console.error(result.errors);
        }
    });
});
