from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # Add this import
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)
CORS(app)  # Add this line to enable CORS for all routes

# Configuration
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Dictionary to store download progress
progress_dict = {}

def download_video(url, filename, format_id):
    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/{filename}.%(ext)s',
            'format': format_id,
            'progress_hooks': [lambda d: progress_hook(d, filename)]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Optionally store video title in progress_dict
            progress_dict[filename]['title'] = info.get('title', f'Video {filename}')
    except Exception as e:
        progress_dict[filename] = {'status': 'error', 'message': str(e)}

def progress_hook(d, filename):
    if d['status'] == 'downloading':
        progress = d.get('_percent_str', '0%')
        eta = d.get('_eta_str', 'N/A')
        # Update or initialize the progress entry
        if filename not in progress_dict:
            progress_dict[filename] = {'status': 'downloading'}
        progress_dict[filename].update({
            'status': 'downloading',
            'progress': progress,
            'eta': eta
        })
    elif d['status'] == 'finished':
        if filename not in progress_dict:
            progress_dict[filename] = {}
        progress_dict[filename].update({
            'status': 'finished',
            'progress': '100%',
            'eta': '0s'
        })

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    url = data.get('url')
    format_id = data.get('format', 'best')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Validate YouTube URL
    import re
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    if not re.match(youtube_regex, url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    # Generate unique filename
    filename = str(uuid.uuid4())
    
    # Initialize progress tracking
    progress_dict[filename] = {'status': 'starting'}
    
    # Start download in a separate thread
    thread = threading.Thread(target=download_video, args=(url, filename, format_id))
    thread.start()
    
    return jsonify({'filename': filename, 'status': 'started'})

@app.route('/progress/<filename>')
def get_progress(filename):
    progress = progress_dict.get(filename, {'status': 'not_found'})
    return jsonify(progress)

@app.route('/download/<filename>')
def download_file(filename):
    # Find the actual file with the correct extension
    for ext in ['.mp4', '.webm', '.mkv', '.mov', '.avi']:
        filepath = f"{DOWNLOAD_DIR}/{filename}{ext}"
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404

# Use the PORT environment variable provided by Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) # Set debug=False for production
