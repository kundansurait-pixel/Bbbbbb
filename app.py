from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best[height<=720]/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'geo_bypass_country': 'IN',
        # Anti-bot headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Redmi Note 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        },
        # Use Android client to bypass bot detection
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Find best mp4 format
        video_url = None
        if 'formats' in info:
            # Try to get direct mp4
            for f in reversed(info['formats']):
                if f.get('ext') == 'mp4' and f.get('url') and f.get('height', 0) <= 720:
                    video_url = f['url']
                    break
            # Fallback to any format
            if not video_url:
                video_url = info['formats'][-1]['url']
        
        if not video_url:
            video_url = info.get('url')
        
        return {
            'video_url': video_url,
            'title': info.get('title', ''),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'video_id': video_id
        }

@app.route('/')
def home():
    return jsonify({'status': 'BharatTube Server Running!', 'version': '2.0'})

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
    
    resp = requests.get(video_url, headers=headers, stream=True, timeout=30)
    
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
