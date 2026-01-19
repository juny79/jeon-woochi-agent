"""
간단한 비디오 파일 서버
Streamlit과 병렬로 실행되어 비디오를 HTTP로 스트리밍합니다.
"""
from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route('/videos/<filename>')
def serve_video(filename):
    """비디오 파일을 HTTP로 스트리밍"""
    video_path = os.path.join('videos', filename)
    
    if not os.path.exists(video_path):
        return "File not found", 404
    
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=False,
    )

@app.route('/health')
def health():
    """헬스 체크"""
    return {"status": "ok"}

if __name__ == '__main__':
    # 포트 8889에서 실행
    app.run(host='127.0.0.1', port=8889, debug=False)
