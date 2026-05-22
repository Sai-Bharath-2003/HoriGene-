from flask import Flask
from flask_cors import CORS

from app.core.database import init_db
from app.api.search  import search_bp
from app.api.protein import protein_bp
from app.api.data    import data_bp


def create_app():
    app = Flask(__name__)

    # Allow the Angular dev server (port 4200) and any other origin during dev.
    # In production replace "*" with your actual domain.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure the database and all tables exist on startup
    init_db()

    # Register blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(protein_bp)
    app.register_blueprint(data_bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        return {"status": "ok", "service": "HoriGene Backend"}

    return app
