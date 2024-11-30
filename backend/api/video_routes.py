import os
import time
from threading import Thread
from pytubefix import YouTube
from moviepy.video.io.VideoFileClip  import VideoFileClip
from flask import Blueprint, request, jsonify
from init import overview_chain, searcher

video_bp  = Blueprint('video_routes', __name__, url_prefix='/api/videos')
video_out_dir = './downloads'

tasks = {}
@video_bp.route('/analyze', methods=['POST'])
def analyze_video():
    # Logic for analyzing a video
    data = request.get_json()
    youtube_url = data.get('youtubeURL')

    task_id = str(int(time.time()))
    tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Processing the video",
        "video": {
            "title": "",
            "id": "",
            "url": youtube_url
        }
    }
    # Start the background process
    thread = Thread(target=process_video, args=(youtube_url, task_id))
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def process_video(youtube_url, task_id):
    try:
        yt = YouTube(youtube_url)
        video_title = yt.title

        stream = yt.streams.first()
        video_out_path = stream.download(video_out_dir)

        audio_out_dir = os.path.join(video_out_dir, 'audio')
        os.makedirs(audio_out_dir, exist_ok=True)
        audio_out_path = os.path.join(audio_out_dir, f'{video_title}.wav')
        video = VideoFileClip(video_out_path)
        audio = video.audio
        audio.write_audiofile(audio_out_path)
        video.close()
        audio.close()

        tasks[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Successfully processed the video",
            "video": {
                "title": video_title,
                "id": yt.video_id,
                "url": youtube_url
            }
        }
    except Exception as e:
        print(e)
    return 

@video_bp.route('/progress/<task_id>', methods=['GET'])
def progress(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    return jsonify({
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "video": {
            "title": task["video"]["title"],
            "id": task["video"]["id"],
            "url": task["video"]["url"]
        }
    })

@video_bp.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"status": "error", "message": "Query is required"}), 400

    task_id = str(int(time.time()))
    # Start the background process
    # thread = Thread(target=process_query, args=(task_id, query))
    # thread.start()
    result = overview_chain.process(query)
    if result['success']:
        search_query = overview_chain.generate_search_query(result['data'])
        print("Search Query: {} | Original Query: {}".format(search_query, query))
        search_result = searcher.search(search_query)
        
        if search_result['success']:
            videos = search_result['data']
            return jsonify({"status": "success", "task_id": task_id, "videos": videos})

    return jsonify({"status": "error", "message": "Failed to process the query"}), 500