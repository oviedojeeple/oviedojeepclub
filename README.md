# Oviedo Jeep Club Web Application

The Oviedo Jeep Club Web Application is a Flask-based project designed to serve as the online presence for the club. It combines a Python backend with HTML templates and static assets (CSS, JavaScript, images) to deliver a responsive and interactive experience. This README provides an overview of each file, instructions for installation and usage, and guidelines for contribution.

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

## Overview

This project is built using Python (with Flask as the web framework) to manage routing, handle business logic, and render HTML pages. The front end is developed with HTML, CSS, and JavaScript to ensure a modern and responsive design. The application provides a main landing page along with pages for privacy policies and data deletion requests.

## Repository Structure

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
- **Virtual Environment (optional but recommended):** For dependency management.

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

## Contributing

Contributions are welcome! Here’s how you can help improve the project:

1. **Fork the Repository:**  
   Create your own copy by clicking the “Fork” button on GitHub.
2. **Create a Feature Branch:**

   ```bash
   git checkout -b feature/my-feature
3. **Make Your Changes:**  
   Commit changes with clear messages.
4. **Push to Your Branch:**

   ```bash
   git push origin feature/my-feature
5. **Submit a Pull Request:**  
   Open a PR on GitHub with a description of your changes.

## License

This project is distributed under the terms of the MIT License. See the [LICENSE](https://github.com/oviedojeeple/oviedojeepclub/blob/main/LICENSE) file for details.

## Contact

For questions, suggestions, or further details, please contact the project maintainers.
