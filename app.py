import whisper
from flask import Flask, request, jsonify
import os
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "https://py.laneterraleverapi.org"}},
    supports_credentials=True,
)

# Load the Whisper model
model = whisper.load_model("large")  # Choose between "tiny", "base", "small", "medium", "large" based on your needs and resources

@app.route("/")
def index():
    return {"STATUS": "SUCCESS", "CODE": 200}

@app.route("/whisper_asr", methods=["POST"])
def perform_asr():
  # Check if the post request has the file part
  if 'audio_file' not in request.files:
      return jsonify({'error': 'No file part'}), 400
  file = request.files['audio_file']

  if file.filename == '':
      return jsonify({'error': 'No selected file'}), 400

  if file and file.filename.lower().endswith('.mp3'):      
      audio_data = file.read()
      result_segments = model.transcribe(audio_data)

      transcription_details = []

      for segment in result_segments["segments"]:
          start_time = segment['start']
          end_time = segment['end']
          text = segment['text']

          transcription_details.append({
              'start_time': start_time,
              'end_time': end_time,
              'text': text
          })

      return jsonify(transcription_details)
  else:
    return jsonify({'error': 'Other General Error'}), 400