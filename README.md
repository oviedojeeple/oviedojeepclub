# Oviedo Jeep Club Web Application

## Overview

The Oviedo Jeep Club Web Application is a Flask-based platform designed to manage club memberships and synchronize public events from the club's Facebook Page. It leverages Azure Entra ID B2C for secure user authentication and utilizes the Facebook Graph API to keep the events section current. The application is hosted on Azure App Service, ensuring scalability and reliable performance.

## Features

- **User Authentication**: Secure login using Azure Entra ID B2C, supporting email/password authentication.
- **Membership Management**: Efficient handling of membership registration, renewals, and cancellations.
- **Membership Payments Processing**: Use of Square as payment processor for New Membership and Renewals
- **Facebook Events Synchronization**: Automatic synchronization of public events from the [Oviedo Jeep Club Facebook Page](https://www.facebook.com/oviedojeeple) using the Facebook Graph API.
- **Email Communications**: Automated email notifications via Azure Email Communication Service.
- **Secure Sessions**: Enhanced session security with dynamic secret key generation.
- **Responsive Design**: User-friendly interface compatible with various devices.

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
  - [Root-Level Files](#root-level-files)
  - [Templates](#templates)
  - [Static Assets](#static-assets)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Development](#development)
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
│   └── ...
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
  A shell script designed to help you initialize and run the web application. It may set up environment variables, start the Flask server, or perform other startup tasks.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/startup.sh)

- **requirements.txt**  
  Contains the list of Python dependencies required to run the application (e.g., Flask, and any other libraries used). Install these with pip.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/requirements.txt)

- **app.py**  
  The main application file that defines the Flask app. It contains the route definitions, controller logic, and functions to render the templates. This file is the entry point of the application when running locally.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/app.py)

- **LICENSE**  
  The licensing file for the project. This file details the terms under which the software is distributed.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/LICENSE)

### Templates

All HTML templates are stored in the `templates` directory. These files are rendered by the Flask app to create dynamic web pages.

- **templates/index.html**  
  The landing page of the application. It typically contains the main content, navigation links, and embedded resources.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/templates/index.html)

- **templates/delete_data.html**  
  A dedicated page to manage data deletion requests. This page might include instructions or forms to help users remove their data from the system.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/templates/delete_data.html)

- **templates/privacy.html**  
  Provides details about the privacy policies of the club, informing users how their data is used and protected.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/templates/privacy.html)

### Static Assets

Static files are served from the `static` directory. This includes styling, images, and client-side JavaScript.

- **static/style.css**  
  The main stylesheet for the application. This file defines the layout, typography, color schemes, and responsive behavior of the website.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/style.css)

- **static/favicon.ico**  
  The favicon for the website, which appears in the browser tab.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/favicon.ico)

- **static/images/ojc.png**  
  The Oviedo Jeep Club logo.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/images/ojc.png)

- **static/images/GoInkit.png**  
  Our partner GoInkIt's logo.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/images/GoInkit.png)

- **static/scripts/profile.js**  
  A JavaScript file that manages profile-related interactions, such as updating user details or handling profile events.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/scripts/profile.js)

- **static/scripts/payment.js**  
  This script handles payment-related functionality, likely including form validations, payment gateway integrations, or transaction processing.  
  [View File](https://github.com/oviedojeeple/oviedojeepclub/blob/main/static/scripts/payment.js)

## Setup and Installation

### Prerequisites

- **Python 3.x:** Ensure Python is installed on your system.
- **Pip:** The Python package installer.
- **Azure Entra ID B2C tenant configured
- **Facebook Developer account with access to the Graph API
- **Square Developer account with access to the Payments API

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
   export FACEBOOK_PAGE_ID="your-facebook-page-id"
   export FACEBOOK_ACCESS_TOKEN="your-facebook-access-token"
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

Happy Jeeping! 🛞🌲 o|||||||o

