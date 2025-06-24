# VeeKenya

VeeKenya is a Django-based web application. This project includes user management, sponsorships, donations, compliance reporting, and more, with a focus on modularity and maintainability.

## Features
- User and profile management
- Child sponsorship and donation tracking
- Compliance and audit logging
- Admin dashboard and user management
- Email notifications and templates

## Project Structure
- `core/` - Main Django app (models, views, forms, templates, static files)
- `veekenya/` - Project settings and configuration
- `staticfiles/` - Collected static files for deployment
- `db.sqlite3` - SQLite database (for development)
- `manage.py` - Django management script

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip

### Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd veekenya
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply migrations:
   ```bash
   python manage.py migrate
   ```
5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```bash
   python manage.py runserver
   ```

### Static Files
To collect static files for production:
```bash
python manage.py collectstatic
```

## Running Tests
```bash
python manage.py test
```

## License
Specify your license here.

## Contact
For questions or support, contact the project maintainer. 