from flask_cors import CORS
from flask import Flask, request, jsonify, Blueprint, send_from_directory
from api.video_routes import video_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(video_bp)
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'

if __name__ == "__main__":
    app.run(debug=True)
    # Register Blueprints