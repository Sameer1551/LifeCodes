# FastAPI Secure Starter

## Purpose
A production-ready FastAPI starter template featuring secure password hashing, JWT authentication, and environment-based configuration management.

## Features
*   **JWT Authentication**: Secure token generation and validation.
*   **Password Hashing**: Uses `passlib` with `bcrypt` (industry standard).
*   **Configuration**: Environment variable management via `pydantic-settings`.
*   **Modern Python**: Uses type hints and modern datetime standards.

## Project Structure
*   `config.py`: Manages app settings (loaded from `.env` or system env).
*   `jwt_helper.py`: Low-level JWT encoding/decoding logic.
*   `auth.py`: Authentication routes (`/auth/token`) and dependencies.
*   `main.py`: Application entry point.

## Requirements
*   Python 3.9+
*   See `requirements.txt` for dependencies.

## How to Run

1.  **Setup Environment**
    Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

2.  **Configuration**
    Create a `.env` file in the root directory:
    ```env
    JWT_SECRET=your_super_secret_key_change_this
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ```

3.  **Run Server**
    ```bash
    uvicorn main:app --reload
    ```

4.  **Test API**
    Visit `http://127.0.0.1:8000/docs`.
    *   Use the "Authorize" button.
    *   Login with credentials: `bob@example.com` / `supersecret`.
    *   Access the `/protected` endpoint.
