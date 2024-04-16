import sys
import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import whisper
import requests
import uuid

# Load the Whisper model
model = whisper.load_model("large")  # Choose between "tiny", "base", "small", "medium", "large" based on your needs and resources

def generate_unique_filename(extension=".txt"):
    unique_filename = str(uuid.uuid4()) + extension
    return unique_filename

def send_email(file_id, email):
    # Create a link to the account creation page with the token
    link = f"{os.getenv('base_url_react')}/transcription/{file_id}"

    # Email content with the link
    email_body = f"""Your audio file has finished processing. Click the link below to add the finishing touches to your generated transcript.\n\n{link}"""

    aws_region = "us-east-2"

    # Create a new SES resource and specify a region.
    client = boto3.client(
        "ses",
        region_name=aws_region,
        aws_access_key_id=os.getenv("aws_access_key_id"),
        aws_secret_access_key=os.getenv("aws_secret_access_key"),
    )

    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                "ToAddresses": [email],
            },
            Message={
                "Body": {
                    "Text": {
                        "Charset": "UTF-8",
                        "Data": email_body,
                    },
                },
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": "LT Transcription Tool Automated Message",
                },
            },
            Source="no-reply@laneterraleverapi.org",  # Your verified address
        )
    except ClientError as e:
        print(f"An error occurred: {e.response['Error']['Message']}")
    else:
        print(f"Email sent! Message ID: {response['MessageId']}")

def speaker_diarization(file_path):
  # Replace YOUR_DEEPGRAM_API_KEY with your actual API key
  api_key = os.getenv('deepgram_api_key')

  # Construct the API endpoint
  url = 'https://api.deepgram.com/v1/listen'
  params = {
      'diarize': 'true',
      'punctuate': 'true',
      'utterances': 'true'
  }
  headers = {
      'Authorization': f'Token {api_key}',
      'Content-Type': 'audio/mp3'
  }

  # Open the file in binary read mode
  with open(file_path, 'rb') as file:
      # Make the API request
      response = requests.post(url, headers=headers, params=params, data=file)
      
  # Check for successful response
  if response.status_code == 200:
      # Parse the JSON response
      response_json = response.json()
      # Extract utterances
      utterances = response_json.get('results', {}).get('utterances', [])
      
      # List to hold speaker IDs and timestamps
      speaker_details = []
      
      # Collect speaker ID and timestamps
      for utterance in utterances:
          speaker_id = utterance.get('speaker')
          timestamp = utterance.get('start')
          end_timestamp = utterance.get('end')
          
          speaker_detail = {
              'speaker_id': speaker_id,
              'start_timestamp': timestamp,
              'end_timestamp': end_timestamp
          }
          
          speaker_details.append(speaker_detail)
      
      # Now speaker_details contains the requested information
      return speaker_details
  else:
      print(f"Error: API request failed with status code {response.status_code}")

def display_transcript(transcript_data):
    # Generate a filename with the current timestamp
    
    filename = generate_unique_filename('.txt')
    
    with open(f'./transcripts/{filename}', 'w') as file:
        # Initialize previous speaker and start time for combining segments
        previous_speaker_ids = None
        segment_start_time = None
        segment_texts = []

        # Helper function to write segments to the file
        def write_segment(speaker_ids, start_time, end_time, texts):
            speaker_label = " & ".join(f"Speaker {speaker_id}" for speaker_id in speaker_ids)
            # Write combined speaker/timestamp line
            file.write(f"[{speaker_label}] ({start_time}s - {end_time}s):\n")
            # Write each text segment separated by newlines
            for text in texts:
                file.write(text + "\n")
            file.write("\n")

        for segment in transcript_data:
            # If the segment has the same speaker(s), combine the texts
            if segment['speaker_ids'] == previous_speaker_ids:
                segment_texts.append(segment['text'])
                end_time = segment['end_time']  # Update the end time to the current segment's end time
            else:
                # If we have a previous speaker, write the combined segment
                if previous_speaker_ids is not None:
                    write_segment(previous_speaker_ids, segment_start_time, end_time, segment_texts)
                
                # Reset for the new speaker segment
                previous_speaker_ids = segment['speaker_ids']
                segment_start_time = segment['start_time']
                end_time = segment['end_time']
                segment_texts = [segment['text']]

        # Make sure to write the last segment
        if previous_speaker_ids is not None:
            write_segment(previous_speaker_ids, segment_start_time, end_time, segment_texts)

    return filename

def combine_speaker_and_transcription(speaker_results, transcription_details):
    combined_transcript = []
    speaker_lines = {}  # To hold the lines spoken by each speaker
    
    def calculate_overlap(speaker, trans_start, trans_end):
        overlap_start = max(speaker['start_timestamp'], trans_start)
        overlap_end = min(speaker['end_timestamp'], trans_end)
        
        overlap_duration = max(0, overlap_end - overlap_start)
        trans_duration = trans_end - trans_start 
        
        # Ensure the trans_duration is at least 0.1 seconds to prevent division by zero
        trans_duration = max(trans_duration, 0.1)
        
        return overlap_duration / trans_duration  # This is the overlap percentage

    # For each transcript segment, determine the corresponding speaker
    for transcription in transcription_details:
        trans_start = round(transcription['start_time'], 1)
        trans_end = round(transcription['end_time'], 1)

        # Generate list of (speaker, overlap_percentage) tuples
        overlap_list = [
            (speaker['speaker_id'], calculate_overlap(speaker, trans_start, trans_end)) 
            for speaker in speaker_results
        ]

        # Sort by overlap percentage in descending order
        overlap_list.sort(key=lambda x: -x[1])
        
        # Determine the speakers for this segment
        chosen_speakers = set()  # Use a set for unique speaker IDs
        for speaker_id, overlap_percentage in overlap_list:
            if overlap_percentage >= 0.8:
                chosen_speakers.add(speaker_id)
                break
            elif overlap_percentage > 0:
                chosen_speakers.add(speaker_id)

        # Create the output structure if speakers have been identified
        if chosen_speakers:
            combined_segment = {
                'speaker_ids': list(chosen_speakers), 
                'start_time': trans_start,
                'end_time': trans_end, 
                'text': transcription['text']
            }
            combined_transcript.append(combined_segment)
            
            # Record the lines for speaker summaries
            for speaker_id in chosen_speakers:
                if speaker_id not in speaker_lines:
                    speaker_lines[speaker_id] = []
                speaker_lines[speaker_id].append(transcription['text'])  # Add text to speaker
        else:
            print(f"No speaker found for the segment {trans_start}s - {trans_end}s.")
    
    # Generate speaker summaries with the first few lines
    speaker_summaries = {f"Speaker {speaker_id}": " ".join(lines[:3]) for speaker_id, lines in speaker_lines.items()}

    return combined_transcript, speaker_summaries

def main():
  with open('./output.txt', 'a') as file:
    audio_file_path = sys.argv[1]
    email = sys.argv[2]
    file.write(f"{audio_file_path} + {email}")
    speaker_results = speaker_diarization(audio_file_path)
    file.write("HERE 1")
    result_segments = model.transcribe(audio_file_path)
    file.write("HERE 2")
    transcription_details = []
    for segment in result_segments["segments"]:
        transcription_details.append({
            'start_time': segment['start'],
            'end_time': segment['end'],
            'text': segment['text']
        })

    full_transcript, speaker_summaries = combine_speaker_and_transcription(speaker_results, transcription_details)
    file.write("HERE 3")
    transcript_file, file_id = display_transcript(full_transcript)
    file.write("HERE 4")
    # Email the result
    send_email(file_id, email)
    file.write("HERE 5")

    with open(f"./transcripts/{transcript_file}", 'rb') as f:
      files = {'file': (transcript_file, f)}
      # POST request to the server
      requests.post("https://py.laneterraleverapi.org/transcripts/upload", files=files)
    file.write("HERE 6")
    



if __name__ == "__main__":
    main()