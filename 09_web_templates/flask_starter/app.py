from flask import Flask, jsonify, g
from config import Config
from auth import auth_bp, jwt_required

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints
    app.register_blueprint(auth_bp)

    @app.route("/ping")
    def ping():
        return jsonify({"msg": "pong"})

    @app.route("/protected")
    @jwt_required
    def protected():
        # Access the user stored in g by the decorator
        user = g.current_user
        return jsonify({"msg": f"Hello {user} – you are authorized!"})

    return app


if __name__ == "__main__":
    flask_app = create_app()
    # Note: debug=True enables the debugger and auto-reload
    flask_app.run(host="0.0.0.0", port=5000, debug=True)
