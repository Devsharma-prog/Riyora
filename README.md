# Riyora

A modern authentication and e-commerce demonstration platform built with Flask.

Riyora started as an e-commerce project and evolved into a portfolio application focused on authentication, security, payment integration, session management, and modern UI/UX design. The goal of the project is to demonstrate practical full-stack development concepts in a clean and professional way.

> This project is intended for educational and portfolio purposes only. Products, orders, and payments are part of a demonstration environment and do not represent a real commercial store.


## Live Demo

https://riyora.onrender.com

> **Note**
>
> This application is hosted on Render's free tier.
> Initial loading may take up to 60 seconds if the server is sleeping.

## Features

- Google OAuth Authentication
- Admin Dashboard
- PayPal Integration
- UPI Support
- Dark / Light Theme
## Features

* Google OAuth Authentication
* Role-Based Admin Access
* Product Catalog & Cart System
* PayPal Integration
* UPI Support
* Dark & Light Theme
* Responsive Design
* Admin Dashboard
* Docker Support



Examples:

* Homepage
* Products
* Login
* Profile
* Admin Dashboard

## Tech Stack

### Backend

* Python
* Flask
* SQLite

### Frontend

* HTML
* CSS
* JavaScript

### Integrations

* Google OAuth
* PayPal

### Deployment

* Docker
* Gunicorn

## Project Structure

```text
riyora/
├── app.py
├── templates/
├── static/
├── assets/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Getting Started

Clone the repository:

```bash
git clone https://github.com/your-username/riyora.git
cd riyora
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a .env file and configure:

```env
SECRET_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

PAYPAL_CLIENT_ID=
PAYPAL_SECRET=

ADMIN_GOOGLE_EMAIL=
```

Run the application:

```bash
python app.py
```

Visit:

```text
http://127.0.0.1:5000
```

## Admin Access

Administrator access is restricted through Google Authentication.

Only the email configured in:

```env
ADMIN_GOOGLE_EMAIL
```

receives administrative privileges.

## Why I Built This

I created Riyora to strengthen my understanding of:

* Authentication Systems
* Session Management
* Payment Integration
* Flask Development
* Secure Web Practices
* Modern UI/UX Design
* Deployment Workflows

The project also serves as a portfolio showcase of my full-stack development skills.

## Future Improvements

* Analytics Dashboard
* Product Search Enhancements
* Order Insights
* Role-Based Permissions
* PostgreSQL Support

