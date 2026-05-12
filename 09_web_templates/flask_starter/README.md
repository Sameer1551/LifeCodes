# flask_starter

## Purpose
A minimal, secure Flask starter with JWT authentication and password hashing.

## Changes & Upgrades
*   **Security**: Uses `passlib[bcrypt]` for robust password hashing.
*   **Architecture**: Decoupled JWT logic from Flask context (easier to test).
*   **Code Quality**: Uses Flask `g` object for request context and type hints.
*   **Config**: Class-based configuration structure.

## Files
*   `app.py`: Application entry point.
*   `auth.py`: Authentication routes and decorators.
*   `security.py`: Password hashing utilities.
*   `jwt_helper.py`: Pure JWT encoding/decoding logic.
*   `config.py`: Configuration management.

## How to run

1.  **Setup Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

2.  **Run Server**
    ```bash
    python app.py
    ```

3.  **Test Endpoints**
    *   **Ping**: `GET http://127.0.0.1:5000/ping`
    *   **Login**: `POST http://127.0.0.1:5000/auth/login`
        *   Body: `{"email": "alice@example.com", "password": "password123"}`
    *   **Protected**: `GET http://127.0.0.1:5000/protected`
        *   Header: `Authorization: Bearer <access_token>`
