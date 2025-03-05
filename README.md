# Job Board Backend

Welcome to the **Job Board Backend** project! This is a powerful, real-world backend system designed to power a job board platform with robust role management, efficient data retrieval, and seamless API integration with modern backend development practices.

## Project Overview

The Job Board Backend is a case study in creating a scalable, feature-rich backend for a job board platform. It powers job postings, user applications, and advanced search functionality while ensuring security and performance. With comprehensive API documentation and a modular design, it’s built to integrate seamlessly with any frontend.

## Project Goals

- **API Development**: Deliver a robust set of APIs for managing job postings, categories, and applications.
- **Access Control**: Implement secure, role-based authentication for admins and users.
- **Database Efficiency**: Optimize job search with indexing and tailored query performance.

## Technologies Used

| **Technology** | **Purpose**                       |
|-----------------|------------------------------------|
| **Django**     | High-level Python framework for rapid, secure development |
| **Django_Rest_framework**     | High-level Python framework for rapid, secure, API development |
| **PostgreSQL** | Relational database for storing and querying job data     |
| **JWT**        | JSON Web Tokens for secure, role-based authentication     |
| **Swagger**    | Interactive API documentation for developers              |
| **Redis**      | In-memory database for caching                            |
| **Celery**     | Asynchronous task queue system, email notification        |
| **Docker**     | Containerization        |
| **Docker-compose**     | Building and running multiple services       |
| **Git flow**     | Version control strategy        |

## Key Features

### Authentication
- Secure registration and login with JWT authentication for `job_seeker`, `employer`, and `admin` roles.

### Job Posting Management
- APIs to create, update, delete, and retrieve job postings.
- Categorize jobs by industry, location, and type (e.g., full-time, remote).

### Role-Based Authentication
- **Admins**: Manage job listings, categories, and oversee platform operations.
- **job_seekers**: Apply to jobs, track applications, and explore opportunities.
- **employers**: Post jobs, update application status and retrieve all jobs they posted

### Optimized Job Search
- Lightning-fast filtering with database indexing.
- Search by location, category, or custom criteria with optimized queries.

### Email notification
- Asynchronous emails triggered by application submission and acceptance, powered by Celery and Redis.

### Pagination
- Efficient list retrieval with configurable page sizes for jobs and applications.

### Containerization
- Docker Compose setup with PostgreSQL, Redis, Django, and Celery services.

### Testing
- Comprehensive unit tests ensuring reliability.

### API Documentation
- Fully documented endpoints using Swagger.
- Accessible at `/api/docs` for easy frontend integration.


## Setup, Installation and running the app
1. **Clone the Repository**  
   ```bash
   git clone https://github.com/DrPlain/alx-project-nexus.git

2. **CD into project directory and install requiremnts** 
   ```bash
   cd alx-project-nexus/job-board-backend

3. **Create a .env file in the project root using the sample below** 
   ```plaintext
   # DJANGO SETUP
   DJANGO_SECRET_KEY=django-insecure-cmts8c-*k(z)o9bawvef=mb=6$b5(zvrpqqwj)s9k)95+o%vcb
   # PostgreSQL Configuration
   POSTGRES_DB=job_board_db
   POSTGRES_USER=job_board_user
   POSTGRES_PASSWORD=job_board_password
   DATABASE_URL=postgres://job_board_user:job_board_password@db:5432/job_board_db

   # Redis Configuration
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0

   # Caching backend
   CACHE_REDIS_URL=redis://redis:6379/1

   # Email Configuration (e.g., Gmail SMTP)
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password

3. **Run project using docker-compose** 
   ```bash
   docker-compose up --build

4. **Access the endpoint below for API documentation** 
   `http://localhost:8000/api/docs/`
