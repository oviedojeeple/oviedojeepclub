document.addEventListener("DOMContentLoaded", async function () {
    console.log("Payment.js loaded");
    const applicationId = window.applicationId;
    console.log("Application ID:", applicationId);
    const locationId = "LBA931MEK4R5V"; // Replace with your actual location ID

    // Initialize Square Payment Form
    const payments = Square.payments(applicationId, 'sandbox');
    const card = await payments.card();
    await card.attach('#card-container');

    // Fetch and Populate Item Library
    const response = await fetch('/items');
    const items = await response.json();
    const selector = document.getElementById('item-selector');
    
    items.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.text = item.item_data.name;
      selector.appendChild(option);
    });

    // Handle Payment Form Submission
    document.querySelector('#payment-form').addEventListener('submit', async function (event) {
      event.preventDefault();
      const itemId = document.getElementById('item-selector').value;
      if (!itemId) {
        alert("Please select a membership type.");
        return;
      }
      const result = await card.tokenize();
      if (result.status === 'OK') {
        document.querySelector('#card-nonce').value = result.token;
        this.submit();
      } else {
        console.error(result.errors);
      }
    });
});
