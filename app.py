from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yt_dlp
import requests
import random

app = Flask(__name__)
CORS(app)

# Multiple user agents to rotate
USER_AGENTS = [
    'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
    'com.google.android.youtube/19.08.35 (Linux; U; Android 12) gzip',
    'com.google.android.youtube/19.10.38 (Linux; U; Android 13) gzip',
]

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Try multiple methods
    methods = [
        # Method 1: Android app client
        {
            'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
            'http_headers': {
                'User-Agent': random.choice(USER_AGENTS),
            }
        },
        # Method 2: iOS client
        {
            'format': 'best[ext=mp4][height<=720]/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                }
            },
        },
        # Method 3: TV client
        {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded'],
                }
            },
        },
        # Method 4: mweb client
        {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb'],
                }
            },
        },
    ]
    
    last_error = None
    for opts in methods:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                video_url = None
                if 'formats' in info:
                    for f in reversed(info['formats']):
                        if f.get('url') and f.get('vcodec') != 'none':
                            video_url = f['url']
                            break
                if not video_url:
                    video_url = info.get('url')
                
                if video_url:
                    return {
                        'video_url': video_url,
                        'title': info.get('title', ''),
                        'thumbnail': info.get('thumbnail', ''),
                        'duration': info.get('duration', 0),
                        'video_id': video_id
                    }
        except Exception as e:
            last_error = str(e)
            continue
    
    raise Exception(f"सभी methods failed: {last_error}")

@app.route('/')
def home():
    return jsonify({'status': 'BharatTube Server Running!', 'version': '3.0'})

@app.route('/api/video')
def get_video():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({'error': 'Video ID required'}), 400
    try:
        info = get_video_info(video_id)
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/proxy')
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'URL required'}), 400
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
        'Referer': 'https://www.youtube.com/',
        'Origin': 'https://www.youtube.com',
    }
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']
    
    resp = requests.get(video_url, headers=headers, stream=True, timeout=60)
    
    def generate():
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                yield chunk
    
    response = Response(
        generate(),
        status=resp.status_code,
        content_type=resp.headers.get('Content-Type', 'video/mp4')
    )
    if 'Content-Range' in resp.headers:
        response.headers['Content-Range'] = resp.headers['Content-Range']
    if 'Content-Length' in resp.headers:
        response.headers['Content-Length'] = resp.headers['Content-Length']
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
