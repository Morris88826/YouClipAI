import os
import time
import json
import whisper
from threading import Thread
from pytubefix import YouTube
from moviepy.video.io.VideoFileClip  import VideoFileClip
from flask import Blueprint, request, jsonify
from init import overview_chain, searcher
from pydub import AudioSegment
from pydub.utils import make_chunks

video_bp  = Blueprint('video_routes', __name__, url_prefix='/api/videos')
download_dir='./downloads'
asr_model = whisper.load_model("turbo")

tasks = {}
@video_bp.route('/fetch', methods=['POST'])
def fetch_video():
    # Logic for analyzing a video
    data = request.get_json()
    youtube_url = data.get('youtubeURL')

    task_id = str(int(time.time()))
    tasks[task_id] = {
        "task_type": "fetch_video",
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
    thread = Thread(target=_fetch_video, args=(youtube_url, task_id))
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def _fetch_video(youtube_url, task_id):
    try:
        yt = YouTube(youtube_url)
        video_url = yt.streams.first().url
        video_id = yt.video_id
        video_title = yt.title

        video_out_dir = os.path.join(download_dir, video_id)
        if os.path.exists(video_out_dir):
            metdata = os.path.join(video_out_dir, 'metadata.json')
            if os.path.exists(metdata):
                with open(metdata, 'r') as f:
                    metadata = json.load(f)
                tasks[task_id] = {
                    "task_type": "fetch_video",
                    "status": "completed",
                    "progress": 100,
                    "message": "Successfully load the video",
                    "video": {
                        "title": metadata["title"],
                        "id": metadata["id"],
                        "url": metadata["url"]
                    }
                }
                return

        os.makedirs(video_out_dir, exist_ok=True)

        stream = yt.streams.first()
        video_out_path = stream.download(video_out_dir, filename='raw_video.mp4')

        audio_out_path = os.path.join(video_out_dir, f'raw_audio.wav')
        video = VideoFileClip(video_out_path)
        audio = video.audio
        audio.write_audiofile(audio_out_path)
        video.close()
        audio.close()

        metadata = {
            "title": video_title,
            "id": video_id,
            "url": video_url
        }

        tasks[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Successfully processed the video",
            "video": metadata
        }


        with open(os.path.join(video_out_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)

    except Exception as e:
        tasks[task_id] = {
            "status": "error",
            "progress": 100,
            "message": str(e),
            "video": {
                "title": "",
                "id": "",
                "url": youtube_url
            }
        }
    return 

@video_bp.route('/progress/<task_id>', methods=['GET'])
def progress(task_id):
    task = tasks.get(task_id)
    if not task:
        tasks.pop(task_id)
        return jsonify({"status": "error", "message": "Task not found"}), 404
    
    if task['task_type'] == 'fetch_video':
        p = jsonify({
            "status": task["status"],
            "task_type": task["task_type"],
            "progress": task["progress"],
            "message": task["message"],
            "video": {
                "title": task["video"]["title"],
                "id": task["video"]["id"],
                "url": task["video"]["url"]
            }
        })
    elif task['task_type'] == 'analyze_asr':
        p = jsonify({
            "status": task["status"],
            "task_type": task["task_type"],
            "progress": task["progress"],
            "message": task["message"],
            "num_chunks": task["num_chunks"]
        })

    if task["status"] == "completed":
        tasks.pop(task_id)
    return p

@video_bp.route('/analyze_asr', methods=['POST'])
def analyze_asr():
    data = request.get_json()
    video_id = data.get('video_id')
    video_out_dir = os.path.join(download_dir, video_id)
    if not os.path.exists(video_out_dir):
        return jsonify({"status": "error", "message": "Video not found"}), 404
    
    task_id = str(int(time.time()))
    tasks[task_id] = {
        "task_type": "analyze_asr",
        "status": "processing",
        "progress": 0,
        "message": "Processing the audio",
        "num_chunks": 0
    }
    # Start the background process
    thread = Thread(target=_analyze_asr, args=(video_id, task_id))
    thread.start()
    return jsonify({"status": "success", "task_id": task_id})
    
def _analyze_asr(video_id, task_id, chunk_length_ms=120*1000):
    video_out_dir = os.path.join(download_dir, video_id)
    audio_out_path = os.path.join(video_out_dir, 'raw_audio.wav')
    audio_out_chunk_dir = os.path.join(video_out_dir, 'chunks')
    transcription_out_dir = os.path.join(video_out_dir, 'transcriptions')
    os.makedirs(audio_out_chunk_dir, exist_ok=True)
    os.makedirs(transcription_out_dir, exist_ok=True)
    try:
        audio = AudioSegment.from_file(audio_out_path)
        chunks = make_chunks(audio, chunk_length_ms)

        progress_step = int(100 / len(chunks))
        for i, chunk in enumerate(chunks):
            # Save the chunk to disk
            audio_chunk_path = os.path.join(audio_out_chunk_dir, f"{i:04d}.wav")
            if not os.path.exists(audio_chunk_path):
                chunk.export(audio_chunk_path, format="wav")
            # Transcribe with Whisper
            transcription_out_path = os.path.join(transcription_out_dir, f"{i:04d}.txt")
            if not os.path.exists(transcription_out_path):
                result = asr_model.transcribe(audio_chunk_path)
                with open(transcription_out_path, 'w') as f:
                    f.write(result['text'])
            tasks[task_id]['progress'] += progress_step

        tasks[task_id] = {
            "task_type": "analyze_asr",
            "status": "completed",
            "progress": 100,
            "message": "Successfully processed the audio",
            "num_chunks": len(chunks)
        }
    except Exception as e:
        tasks[task_id] = {
            "task_type": "analyze_asr",
            "status": "error",
            "progress": 100,
            "message": str(e),
            "num_chunks": 0
        }
    return


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