import whisper
from flask import Flask, request, jsonify, send_from_directory, abort
import os
import boto3
from werkzeug.utils import secure_filename
from flask_cors import CORS
from dotenv import load_dotenv
import subprocess


app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "https://py.laneterraleverapi.org"}},
    supports_credentials=True,
)

load_dotenv()

UPLOAD_FOLDER = "./temp_files"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
FILE_DIRECTORY = "./transcripts"


@app.route("/")
def index():
    return {"STATUS": "SUCCESS", "CODE": 200}

@app.route('/get-file')
def get_file():
    # Get the filename from query parameters
    file_name = request.args.get('file_name')
    
    if not file_name:
        # If no filename is provided, return an error response
        return abort(400, description="No file name provided.")

    try:
        # Securely send the file from the specified directory
        return send_from_directory(FILE_DIRECTORY, file_name, as_attachment=True)
    except FileNotFoundError:
        # If the file does not exist, return a 404 error
        return abort(404, description="File not found.")

@app.route("/whisper_asr", methods=["POST"])
def perform_asr():
    # Check if a file or email part is missing in the request
    if 'audio_file' not in request.files or 'email' not in request.form:
        return jsonify({'error': 'No file or email part'}), 400
    
    file = request.files['audio_file']
    email = request.form.get('email')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    allowed_extensions = {'.mp3', '.wav'}
    if file and any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            process = subprocess.Popen(['python', "./perform_asr.py", filepath, email], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return jsonify({'message': 'File Being Processed'}), 200
        except Exception as e:
            os.remove(filepath)
            return jsonify({'error': 'Failed to process the file', 'details': str(e)}), 500

    return jsonify({'error': 'File format not supported. Please upload an MP3 or WAV file.'}), 400