"""
Main web application entry point.
"""

from pathlib import Path
import os
import sys

# Ensure src/ is on Python module search path
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from flask import Flask, send_from_directory, jsonify
from watermarking.config import FRONTEND_DIR, OUTPUT_DIR
from web.routes import api_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/output/<path:filename>")
    def serve_output(filename):
        return send_from_directory(OUTPUT_DIR, filename)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found."}), 404

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print("==================================================")
    print(" JND-Guided Frequency-Domain Watermarking Web App")
    print(f" Server running at: http://localhost:{port}")
    print("==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
