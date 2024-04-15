import whisper
from flask import Flask, request, jsonify
import os
from flask_cors import CORS
from pydub import AudioSegment
import numpy as np
import io

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
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and file.filename.lower().endswith('.mp3'):
        try:
            # Read the file into an audio segment
            audio_segment = AudioSegment.from_file(io.BytesIO(file.read()), format="mp3")
            # Convert audio segment to numpy array
            samples = np.array(audio_segment.get_array_of_samples())

            if audio_segment.channels == 2:  # Check if audio is stereo
                samples = samples.reshape((-1, 2))
                samples = samples.mean(axis=1)  # Convert to mono by averaging channels

            # At this point, 'samples' is a numpy array; you can pass this to Whisper
            result_segments = model.transcribe(samples)

            transcription_details = [{
                'start_time': segment['start'],
                'end_time': segment['end'],
                'text': segment['text']
            } for segment in result_segments["segments"]]
            return jsonify(transcription_details)
        except Exception as e:
            return jsonify({'error': 'Failed to process the file', 'details': str(e)}), 500
    else:
        return jsonify({'error': 'File format not supported. Please upload an MP3 file.'}), 400