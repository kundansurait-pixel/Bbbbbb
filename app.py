from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)  # Allow all domains

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Get direct MP4 url
        video_url = info.get('url')
        title = info.get('title', '')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        
        return {
            'video_url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'video_id': video_id
        }

@app.route('/')
def home():
    return jsonify({'status': 'BharatTube Server Running!', 'version': '1.0'})

@app.route('/api/video')
def get_video():
    video_id = request.args.get('id')
    
    if not video_id:
        return jsonify({'error': 'Video ID required'}), 400
    
    try:
        info = get_video_info(video_id)
        return jsonify({
            'success': True,
            'data': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy')
def proxy_video():
    """Stream video through our server"""
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'URL required'}), 400
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.youtube.com',
    }
    
    # Forward range header if present
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']
    
    resp = requests.get(video_url, headers=headers, stream=True)
    
    def generate():
        for chunk in resp.iter_content(chunk_size=8192):
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
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
