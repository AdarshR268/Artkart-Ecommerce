# Art Kart E-Commerce Website

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.x-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.x-purple.svg)](https://getbootstrap.com/)

An interactive and responsive e-commerce platform designed for art enthusiasts to browse and purchase a wide variety of wall paints. This project combines an engaging user interface with robust backend functionality to deliver a seamless shopping experience.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)


## Features

*   **User Authentication:** Users can register, log in, and manage their profiles.
*   **Product Catalog:** Displays a range of products with categories, descriptions, and images.
*   **Product Reviews and Ratings:** Customers can review and rate products through a modal interface.
*   **Cart Management:** Add, update, and remove items in the cart with real-time updates.
*   **Checkout Process:** Simplified checkout flow with address selection, including a primary address feature.
*   **Offers and Discounts:** Exclusive offers for art and paint categories, with discounts applied at checkout.
*   **Sales Reports:** Filterable reports for sales, with options for daily, weekly, and monthly views, including messages for no orders.
*   **PDF Invoice Generation:** Downloadable PDF invoices for orders using `pdfkit`.
*   **Admin Panel:** Admins can add, edit, and remove products, manage categories, view sales reports, and update offers.

## Tech Stack

*   **Frontend:** HTML, CSS, JavaScript, Bootstrap
*   **Backend:** Django (Python)
*   **Database:** PostgreSQL (or any preferred Django-compatible database)
*   **PDF Generation:** `pdfkit` library


## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/art-kart.git](https://www.google.com/search?q=https://github.com/your-username/art-kart.git)
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd art-kart
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up the database:**
    *   Configure your PostgreSQL database settings in `settings.py`.
    *   Run migrations:
        ```bash
        python manage.py makemigrations
        python manage.py migrate
        ```

6.  **Create a superuser (for admin access):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

## Usage

1.  Access the website in your browser at `http://127.0.0.1:8000/`.
2.  Register or log in as a user to browse and purchase products.
3.  Access the admin panel at `http://127.0.0.1:8000/admin/` using the superuser credentials.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.  Follow these guidelines:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Commit your changes and push to your branch.
5.  Submit a pull request.



