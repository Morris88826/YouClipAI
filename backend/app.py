from flask_cors import CORS
from flask import Flask, request, jsonify, Blueprint
from api.video_routes import video_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(video_bp)


if __name__ == "__main__":
    app.run(debug=True)
    # Register Blueprints