document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, "sandbox");
    const card = await payments.card();
    await card.attach("#card-container");

    // Define the renewPayButton element
    const renewPayButton = document.getElementById("renewPayButton");
    
    // Handle payment for membership renewal
    if (renewPayButton) {
        renewPayButton.addEventListener("click", async function (event) {
            event.preventDefault();
            renewPayButton.disabled = true;
            renewPayButton.textContent = "Processing...";
    
            // Tokenize card details for renewal
            const tokenResult = await card.tokenize();
            if (tokenResult.status !== "OK") {
                showFlashMessage("Error processing payment details. Please try again.", "danger");
                renewPayButton.disabled = false;
                renewPayButton.textContent = "Renew Now";
                return;
            }
            const nonce = tokenResult.token;
            const payload = { nonce }; // Now you have something to send
    
            fetch("/renew-membership", {
                method: "POST",
                credentials: 'same-origin',  // Ensures session cookies are sent
                body: JSON.stringify(payload),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload(); // Refresh to show updates
                } else {
                    showFlashMessage("Payment failed. Please try again.", "danger");
                    renewPayButton.disabled = false;
                    renewPayButton.textContent = "Renew Now";
                }
            })
            .catch((error) => {
                console.error("Error processing payment:", error);
                showFlashMessage("An error occurred. Please try again.", "danger");
                renewPayButton.disabled = false;
                renewPayButton.textContent = "Renew Now";
            });
        });
    }
    
    // Handle Payment Form Submission for Joining
    const joinPayButton = document.querySelector("#card-button");
    if (joinPayButton) {
        joinPayButton.addEventListener("click", async function (event) {
            event.preventDefault();

            // Disable button and change text
            joinPayButton.disabled = true;
            joinPayButton.textContent = "Processing...";

            // Retrieve user input values
            const email = document.getElementById("email").value;
            const displayName = document.getElementById("displayName").value;
            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirmPassword").value;

            // Validate password match
            if (password !== confirmPassword) {
                showFlashMessage("Passwords do not match. Please re-enter.", "danger");
                joinPayButton.disabled = false;
                joinPayButton.textContent = "Pay Membership Fee";
                return;
            }

            // Process Square Payment
            const result = await card.tokenize();
            if (result.status === "OK") {
                document.querySelector("#card-nonce").value = result.token;
                document.querySelector("#payment-form").submit();
            } else {
                console.error(result.errors);
                showFlashMessage("Error processing payment details. Please try again.", "danger");
                joinPayButton.disabled = false;
                joinPayButton.textContent = "Pay Membership Fee";
            }
        });
    }
    
    // Function to display a flash message
    function showFlashMessage(message, category) {
        const flashContainer = document.getElementById("flash-messages");
        if (!flashContainer) return;
        flashContainer.innerHTML = ''; // Clear existing messages
        const flashMessage = document.createElement("div");
        flashMessage.className = `flash-message flash-${category}`;
        flashMessage.textContent = message;
        flashContainer.appendChild(flashMessage);
    }
});
