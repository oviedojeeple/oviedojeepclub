document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Handle payment for membership renewal
    const renewPayButton = document.getElementById("renewPayButton");
    if (renewPayButton) {
        renewPayButton.addEventListener("click", function () {
            handlePayment(renewPayButton, "/renew-membership");
        });
    }

    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, "sandbox");
    const card = await payments.card();
    await card.attach("#card-container");

    // Function to display a flash message
    function showFlashMessage(message, category) {
        const flashContainer = document.getElementById("flash-messages");
        if (!flashContainer) return;

        // Clear existing messages
        flashContainer.innerHTML = '';

        // Create the new flash message
        const flashMessage = document.createElement("div");
        flashMessage.className = `flash-message flash-${category}`;
        flashMessage.textContent = message;
        flashContainer.appendChild(flashMessage);

        // Automatically hide the message after 5 seconds
        setTimeout(() => {
            flashMessage.remove();
        }, 5000);
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

    // Generic function to handle payments and disable buttons
    function handlePayment(button, url) {
        button.disabled = true;
        button.textContent = "Processing...";

        fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    location.reload(); // Refresh to show updates
                } else {
                    showFlashMessage("Payment failed. Please try again.", "danger");
                    button.disabled = false;
                    button.textContent = button.id === "renewPayButton" ? "Pay Now" : "Pay Membership Fee";
                }
            })
            .catch((error) => {
                console.error("Error processing payment:", error);
                showFlashMessage("An error occurred. Please try again.", "danger");
                button.disabled = false;
                button.textContent = button.id === "renewPayButton" ? "Pay Now" : "Pay Membership Fee";
            });
    }
});
