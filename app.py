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
    # Check if the post request has the file part
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['audio_file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.lower().endswith('.mp3'):
        # Ensure filename is secure
        email = request.form['email']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            process = subprocess.Popen(['python', "./perform_asr.py", filepath, email], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # # Process the audio file
            # result_segments = model.transcribe(filepath)

            # transcription_details = []
            # for segment in result_segments["segments"]:
            #     transcription_details.append({
            #         'start_time': segment['start'],
            #         'end_time': segment['end'],
            #         'text': segment['text']
            #     })
            
            # # Once processing is complete, remove the file
            # os.remove(filepath)
            return jsonify({'message': 'File Being Processed'}), 200

        except Exception as e:
            # If something goes wrong, remove the file and return an error
            os.remove(filepath)
            return jsonify({'error': 'Failed to process the file', 'details': str(e)}), 500

    else:
        return jsonify({'error': 'File format not supported. Please upload an MP3 file.'}), 400