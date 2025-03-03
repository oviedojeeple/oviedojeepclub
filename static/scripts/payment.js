document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Show the renew membership section when the renew button is clicked
    const renewButton = document.getElementById("renewButton");
    if (renewButton) {
        renewButton.addEventListener("click", function () {
            document.getElementById("renew-section").style.display = "block";
        });
    }

    // Handle payment for membership renewal
    const renewPayButton = document.getElementById("renewPayButton");
    if (renewPayButton) {
        renewPayButton.addEventListener("click", function () {

            // Disable the button to prevent multiple clicks
            renewPayButton.disabled = true;
            renewPayButton.textContent = "Processing...";
            
            fetch("/renew-membership", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renewPayButton.disabled = false; // Re-enable on success.
                    renewPayButton.textContent = "Pay Now";
                    location.reload(); // Refresh to show new expiration date and flash message
                } else {
                    showFlashMessage("Payment failed. Please try again.", "danger");
                    renewPayButton.disabled = false; // Re-enable on failure
                    renewPayButton.textContent = "Pay Now";
                }
            })
            .catch(error => {
                console.error("Error processing renewal:", error);
                showFlashMessage("An error occurred. Please try again.", "danger");
                renewPayButton.disabled = false; // Re-enable on error
                renewPayButton.textContent = "Pay Now";
            });
        });
    }
    
    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, 'sandbox');
    const card = await payments.card();
    await card.attach('#card-container');
    
    // Flash message handling
    function displayClientFlash(message, category) {
        const flashContainer = document.getElementById("flash-messages");
        if (!flashContainer) return;

        const flashMessage = document.createElement("div");
        flashMessage.className = `alert alert-${category}`;
        flashMessage.textContent = message;
        flashContainer.appendChild(flashMessage);

        // Automatically hide the message after 5 seconds
        setTimeout(() => {
            flashMessage.remove();
        }, 5000);
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
            displayClientFlash("Error processing payment details. Please try again.", "danger");
        }
    });
});
