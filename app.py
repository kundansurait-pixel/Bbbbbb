from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import requests
import random

app = Flask(__name__)
CORS(app)

# Invidious public instances — no bot check!
INVIDIOUS = [
    "https://invidious.nerdvpn.de",
    "https://invidious.privacydev.net", 
    "https://inv.tux.pizza",
    "https://invidious.slipfox.xyz",
    "https://invidious.io.lol",
    "https://vid.puffyan.us",
    "https://yt.artemislena.eu",
    "https://invidious.lunar.icu",
]

def get_video_from_invidious(video_id):
    random.shuffle(INVIDIOUS)
    
    for instance in INVIDIOUS:
        try:
            url = f"{instance}/api/v1/videos/{video_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=10)
            
            if r.status_code != 200:
                continue
                
            data = r.json()
            
            if 'error' in data:
                continue
            
            # Get best mp4 stream
            video_url = None
            formats = data.get('adaptiveFormats', []) + data.get('formatStreams', [])
            
            # Prefer formatStreams (combined audio+video)
            for f in data.get('formatStreams', []):
                if 'mp4' in f.get('type','') or f.get('container') == 'mp4':
                    video_url = f.get('url') or f'{instance}/latest_version?id={video_id}&itag={f.get("itag","22")}'
                    break
            
            # Fallback
            if not video_url and formats:
                for f in formats:
                    if 'mp4' in f.get('type',''):
                        video_url = f.get('url')
                        break
            
            # Last resort — invidious direct stream
            if not video_url:
                video_url = f"{instance}/latest_version?id={video_id}&itag=22"
            
            # Proxy through our server
            proxy_url = f"/api/proxy?url={requests.utils.quote(video_url)}&instance={requests.utils.quote(instance)}"
            
            return {
                'video_url': proxy_url,
                'direct_url': video_url,
                'instance': instance,
                'title': data.get('title', ''),
                'thumbnail': f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                'duration': data.get('lengthSeconds', 0),
                'video_id': video_id
            }
        except Exception as e:
            continue
    
    raise Exception("सभी Invidious servers busy हैं, थोड़ी देर बाद try करें")

@app.route('/')
def home():
    return jsonify({'status': 'BharatTube Server Running!', 'version': '5.0', 'method': 'Invidious'})

@app.route('/api/video')
def get_video():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({'error': 'Video ID required'}), 400
    try:
        info = get_video_from_invidious(video_id)
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/proxy')
def proxy_video():
    video_url = request.args.get('url')
    instance = request.args.get('instance', 'https://invidious.nerdvpn.de')
    
    if not video_url:
        return jsonify({'error': 'URL required'}), 400
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
        'Referer': instance + '/',
        'Origin': instance,
    }
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']
    
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
