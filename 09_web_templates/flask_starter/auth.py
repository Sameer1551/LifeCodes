from functools import wraps
from flask import Blueprint, jsonify, request, current_app, g
from jwt_helper import create_access_token, decode_access_token
from security import verify_password, get_password_hash

# In-memory user store (use a database in production)
# Pre-hashing the password "password123" for the user
_USERS = {
    "alice@example.com": get_password_hash("password123")
}

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticates a user and returns a JWT.
    Expects JSON: { "email": "...", "password": "..." }
    """
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    stored_hash = _USERS.get(email)
    
    # Verify user exists and password matches
    if not stored_hash or not verify_password(password, stored_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate Token
    access_token = create_access_token(
        data={"sub": email},
        secret=current_app.config["JWT_SECRET"],
        algorithm=current_app.config["JWT_ALGORITHM"],
        expires_delta=datetime.timedelta(seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"])
    )
    
    return jsonify({"access_token": access_token, "token_type": "bearer"})


def jwt_required(fn):
    """
    Decorator to protect routes. 
    Validates the Bearer token and injects user identity into 'g'.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
            
        token = auth_header.split(" ", 1)[1]
        
        try:
            payload = decode_access_token(
                token=token, 
                secret=current_app.config["JWT_SECRET"],
                algorithms=[current_app.config["JWT_ALGORITHM"]]
            )
            # Store identity in flask.g for this request
            g.current_user = payload.get("sub")
        except Exception as exc:
            return jsonify({"error": f"Invalid token: {str(exc)}"}), 401

        return fn(*args, **kwargs)
    return wrapper
