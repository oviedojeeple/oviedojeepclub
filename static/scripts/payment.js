document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, 'sandbox');
    const card = await payments.card();
    await card.attach('#card-container');

    // Handle Payment Form Submission
    document.querySelector('#payment-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      
      // Retrieve user input fields
      const email = document.getElementById('email').value;
      const displayName = document.getElementById('displayName').value;
      
      if (!email || !displayName) {
        alert("Please provide both your email and display name.");
        return;
      }
      
      const result = await card.tokenize();
      if (result.status === 'OK') {
        document.querySelector('#card-nonce').value = result.token;
        // Optionally, you could append the email and displayName as hidden fields too.
        // Then, allow the form to submit.
        this.submit();
      } else {
        console.error(result.errors);
      }
    });
});
