# Oviedo Jeep Club Web Application

## Overview

The Oviedo Jeep Club Web Application is a Flask-based platform designed to manage club memberships, process membership payments, and synchronize public events from the club's Facebook Page. It leverages Azure Entra ID B2C for secure user authentication, utilizes the Facebook Graph API to keep events current, and integrates with Square for payment processing. The application is hosted on Azure App Service for scalability and reliable performance.

## Features

- **User Authentication:** Secure login using Azure Entra ID B2C with email/password authentication.
- **Membership Management:** Efficient handling of membership registration, renewals, cancellations, and data deletion requests.
- **Membership Payments Processing:** Integration with Square for processing new memberships and renewals.
- **Facebook Events Synchronization:** Automatic synchronization of public events from the [Oviedo Jeep Club Facebook Page](https://www.facebook.com/oviedojeeple) using the Facebook Graph API.
- **Event Reminder Notifications:**  
  - Automated email reminders are now sent to all active members whose membership expiration date (stored as a timestamp) is prior to the event’s start date.  
  - Reminders are scheduled to be sent 15, 7, or 1 day(s) before the event begins using APScheduler.
- **Email Communications:** Automated emails are sent via Azure Communication Services. Email types include disablement reminders, family invitation emails, membership renewal confirmations, welcome emails, and now event reminders.
- **Secure Sessions:** Enhanced session security with dynamic secret key generation.
- **Responsive Design:** A user-friendly interface that works well on various devices.

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
  - [Root-Level Files](#root-level-files)
  - [Templates](#templates)
  - [Static Assets](#static-assets)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Repository Structure



```
oviedojeepclub/
├── .github/
│   └── workflows/
│       └── azure-webapps-deploy.yml
├── static/
│   ├── css/
│   ├── images/
│   └── js/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── emails/
│       ├── disablement_reminder.html
│       ├── event_reminder.html
│       ├── family_invitation.html
│       ├── membership_renewal.html
│       └── new_membership.html
├── utilities/
│   └── facebook_events.py
├── .gitignore
├── LICENSE
├── README.md
├── app.py
├── event_uploader.py
├── requirements.txt
└── startup.sh
```
Below is a breakdown of the repository’s key files and directories:


### Root-Level Files

- **startup.sh**  
  A shell script to initialize and run the web application (e.g., setting environment variables and starting the Flask server).  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/startup.sh)

- **requirements.txt**  
  Contains the Python dependencies required for the application (e.g., Flask, APScheduler, Azure SDKs).  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/requirements.txt)

- **app.py**  
  The main application file that defines the Flask app, route definitions, business logic, and email communications—including the new event reminder functionality.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/app.py)

- **LICENSE**  
  The licensing file for the project.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/LICENSE)

### Templates

HTML templates are stored in the `templates` directory. In addition to the standard pages (index, privacy, delete data), there is now a dedicated folder for email templates:
  
- **templates/emails/event_reminder.html**  
  The new email template that notifies members about upcoming events. This template uses variables such as `{{ event_name }}`, `{{ recipient_name }}`, `{{ days_left }}`, and `{{ current_year }}`.

### Static Assets

Static files include CSS, images, and JavaScript:

- **static/css/style.css**  
  Main stylesheet that defines the layout and responsive design.
  
- **static/images/ojc.png**  
  The Oviedo Jeep Club logo used across the site and in email communications.
  
- **static/images/GoInkit.png**  
  Logo for the partner GoInkit.
  
- **static/js/profile.js** and **static/js/payment.js**  
  JavaScript files that handle profile interactions and payment processing, respectively.

## Setup and Installation

### Prerequisites

- **Python 3.x:** Ensure that Python is installed.
- **Pip:** Python package installer.
- **Azure Entra ID B2C Tenant:** For user authentication.
- **Facebook Developer Account:** With access to the Graph API.
- **Square Developer Account:** For payment processing.
- **Azure Communication Services:** For email communications.

### Installation Steps

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/oviedojeeple/oviedojeepclub.git
   cd oviedojeeple/oviedojeepclub
   
2. **Set Up a Virtual Environment (Optional):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   
3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt

   4. **Run the Application:**

   You can start the application by executing the startup script or by running the Flask app directly:
   
   Using the startup script:
   ```bash
   ./startup.sh

   Or manually:
   ```bash
   python app.py

4. **Configuration:**

   Set environment variables for Azure authentication, email service, and Facebook API access:
  
   ```bash
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_COMM_CONNECTION_STRING="your-azure-communication-connection-string"
   export AZURE_COMM_CONNECTION_STRING_SENDER="your-email-sender-address"
   export FACEBOOK_PAGE_ID="your-facebook-page-id"
   export FACEBOOK_ACCESS_TOKEN="your-facebook-access-token"
   export SQUARE_ACCESS_TOKEN="your-square-access-token"
   export SQUARE_APPLICATION_ID="your-square-application-id"

   ```
  
   Obtain the `FACEBOOK_ACCESS_TOKEN` from the [Facebook Graph API documentation](https://developers.facebook.com/docs/graph-api/get-started/).


## Usage

- Open your web browser and navigate to `http://127.0.0.1:5000` (or the specified port) to view the application.
- The landing page (`index.html`) will load first, with links to the privacy policy and data deletion pages.
- JavaScript files handle interactive components like user profiles and payment processing.

## Development

### Code Organization

- **Backend (`app.py`):**  
  Handles routing, data processing, and rendering HTML templates.
- **Templates:**  
  HTML files in the `templates` folder that structure the website.
- **Static Files:**  
  CSS for styling, JavaScript for interactive features, and images for branding are all located in the `static` folder.

### Customization

- **Styling:**  
  Modify `static/style.css` to change the appearance of the site.
- **JavaScript:**  
  Enhance or update interactivity by editing the files in `static/scripts/`.
- **Templates:**  
  Update content and structure by editing files in the `templates` folder.

## Running the Application

Set Flask application environment variable:

```bash
export FLASK_APP=app.py
```

Run the Flask application:

```bash
flask run
```

Access the application at `http://127.0.0.1:5000/`.

## Deployment

The application is configured for Azure App Service deployment using GitHub Actions (`.github/workflows/azure-webapps-deploy.yml`). Ensure Azure credentials and secrets are set in GitHub repository settings.

Manual deployment instructions: [Microsoft Quickstart guide](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python?tabs=flask).

## Facebook Events Synchronization

The `utilities/facebook_events.py` module interacts with the Facebook Graph API to fetch and update events:

1. Create a Facebook App at [Facebook Developer Portal](https://developers.facebook.com/).
2. Generate a long-lived Access Token with `pages_read_engagement` permission.
3. Schedule synchronization with `event_uploader.py`.

## Email Communications

Automated emails via Azure Email Communication Service. Follow [Azure's documentation](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/send-email) for setup.

## Secure Sessions

Secure sessions with dynamic Flask secret keys. Set the `SECRET_KEY` environment variable accordingly.

## Contribution

To contribute:

1. Fork the repository.
2. Create a new branch:

```bash
git checkout -b feature/your-feature-name
```

3. Commit and push changes:

```bash
git commit -m "Your commit message"
git push origin feature/your-feature-name
```

4. Submit a pull request.

## License

Licensed under the MIT License. See the [LICENSE](LICENSE) file.

## Contact

For inquiries, visit [Oviedo Jeep Club](https://oviedojeepclub.com) or their [Facebook Page](https://www.facebook.com/oviedojeeple).

Happy Jeeping! 🌲 o|||||||o 🌲

