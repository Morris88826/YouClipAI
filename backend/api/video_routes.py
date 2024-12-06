import os
import time
import json
import glob
import shutil
import whisper
import pandas as pd
from threading import Thread, Lock
from pytubefix import YouTube
from moviepy import VideoFileClip
from flask import Blueprint, request, jsonify, url_for, current_app, send_from_directory
from init import overview_chain, search_content_chain, search_youtube
from pydub import AudioSegment
from pydub.utils import make_chunks
from collections import defaultdict

video_bp = Blueprint('video_routes', __name__, url_prefix='/api/videos')
download_dir = './downloads'
asr_model = whisper.load_model("turbo")

tasks = {}
tasks_lock = Lock()  # Lock to manage access to tasks dictionary

# Helper Functions for Thread-Safe Task Updates
def update_task(task_id, updates):
    """Thread-safe method to update task data"""
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id].update(updates)

def get_task(task_id):
    """Thread-safe method to get task data"""
    with tasks_lock:
        return tasks.get(task_id)

@video_bp.route('/progress/<task_id>', methods=['GET'])
def progress(task_id):
    task = get_task(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404

    response = {
        "task_type": task["task_type"],
        "subtask_type": task.get("subtask_type", ""),
        "current_video": task.get("current_video", 0),
        "progress": task["progress"],
        "message": task["message"],
    }
    response["status"] = "completed" if task["progress"] >= 100 and response["subtask_type"] == "" else "processing"

    if response["status"] == "completed":
        response["data"] = task.get("data", {})
        # print(response["data"])
        with tasks_lock:
            tasks.pop(task_id, None)

    elif task["status"] == "error":
        with tasks_lock:
            tasks.pop(task_id, None)
        return jsonify({"status": "error", "message": task["message"]}), 500

    return jsonify(response), 200

@video_bp.route('/advanced_search', methods=['POST'])
def advanced_search():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"status": "error", "message": "Query is required"}), 400

    task_id = str(int(time.time()))

    with tasks_lock:
        tasks[task_id] = {
            "task_type": "advanced_search",
            "status": "processing",
            "progress": 0,
            "message": "Processing the query",
            "data": []
        }

    thread = Thread(target=_advanced_search, args=(task_id, query), daemon=True)
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def _advanced_search(task_id, query):
    try:
        result = overview_chain.process(query)
        if result['success']:
            search_query = overview_chain.generate_search_query(result['data'])
            print("Search Query: {} | Original Query: {}".format(search_query, query))
            preliminary_result = search_youtube.search(search_query)
            if len(preliminary_result['data']) == 0:
                raise Exception("No videos found for the query")
            postprocessed_result = search_youtube.postprocess(preliminary_result, search_query)
            if postprocessed_result['success']:
                videos = postprocessed_result['data']
                update_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": "Successfully processed the query",
                    "data": {
                        "videos": videos,
                        "query": {
                            'query': query,
                            '4w1h': result['data']
                        }
                    }
                })
            else:
                raise Exception("Failed to search for videos")
        else:
            raise Exception("Failed to process the query")
    except Exception as e:
        print("Error in advanced_search: ", e)
        update_task(task_id, {
            "status": "error",
            "progress": 100,
            "message": f"Error in advanced_search: {str(e)}",
            "data": []
        })

@video_bp.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    videos = data.get('videos')
    query = data.get('query', '')


    if not videos:
        return jsonify({"status": "error", "message": "Videos are required"}), 400
    
    task_id = str(int(time.time()))
    with tasks_lock:
        tasks[task_id] = {
            "task_type": "analyze",
            "status": "processing",
            "progress": 0,
            "message": "Processing the videos",
            "data": []
        }

    thread = Thread(target=_analyze, args=(current_app._get_current_object(), videos, task_id, query), daemon=True)
    thread.start()

    return jsonify({"status": "success", "message": "Successfully processed the videos sequentially", "task_id": task_id})

def _analyze(app, videos, task_id, query):
    try:
        datas = []
        for i, video in enumerate(videos):
            update_task(task_id, {
                "progress": 1,
                "subtask_type": "analyze_asr",
                "current_video": i,
                "message": "Transcribing the audio",
            })
            _analyze_asr(video, task_id)
            update_task(task_id, {
                "subtask_type": "search_content",
                "message": "Searching for content",
            })
            metadata = get_task(task_id)['data']
            _search_content(app, task_id, query, metadata)
            datas.extend(get_task(task_id)['data'])

        update_task(task_id, {
            "subtask_type": "",
            "progress": 100,
            "message": "Videos processed successfully",
            "data": datas
        })

    except Exception as e:
        print("Error in analyze: ", e)
        update_task(task_id, {
            "task_type": "analyze",
            "status": "error",
            "progress": 100,
            "message": f"Error in analyze: {str(e)}",
            "data": []
        })

@video_bp.route('/analyze_asr', methods=['POST'])
def analyze_asr():
    data = request.get_json()
    video = data.get('video')

    if not video:
        return jsonify({"status": "error", "message": "Video data is required"}), 400

    task_id = str(int(time.time()))
    with tasks_lock:
        tasks[task_id] = {
            "task_type": "analyze_asr",
            "status": "processing",
            "progress": 0,
            "message": "Processing the audio",
            "data": {}
        }
    
    thread = Thread(target=_analyze_asr, args=(video, task_id), daemon=True)
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def _analyze_asr(video, task_id, chunk_length_ms=120 * 1000):
    try:
        print(video)
        update_task(task_id, {'progress': 5})
        video_out_dir = os.path.join(download_dir, video['id'])
        if not os.path.exists(video_out_dir):
            os.makedirs(video_out_dir, exist_ok=True)

            yt = YouTube(video['url'])
            stream = yt.streams.first()
            video_out_path = stream.download(video_out_dir, filename='raw_video.mp4')
            audio_out_path = os.path.join(video_out_dir, 'raw_audio.wav')
            video_clip = VideoFileClip(video_out_path)
            audio = video_clip.audio
            audio.write_audiofile(audio_out_path)
            video_clip.close()
            audio.close()

        update_task(task_id, {'progress': 10})

        audio_out_path = os.path.join(video_out_dir, 'raw_audio.wav')
        audio_out_chunk_dir = os.path.join(video_out_dir, 'chunks')
        transcription_out_dir = os.path.join(video_out_dir, 'transcriptions')
        os.makedirs(audio_out_chunk_dir, exist_ok=True)
        os.makedirs(transcription_out_dir, exist_ok=True)

        audio = AudioSegment.from_file(audio_out_path)
        chunks = make_chunks(audio, chunk_length_ms)

        progress_step = int(90 / len(chunks))
        for i, chunk in enumerate(chunks):
            audio_chunk_path = os.path.join(audio_out_chunk_dir, f"{i:04d}.wav")
            if not os.path.exists(audio_chunk_path):
                chunk.export(audio_chunk_path, format="wav")

            transcription_out_path = os.path.join(transcription_out_dir, f"{i:04d}.csv")
            if not os.path.exists(transcription_out_path):
                result = asr_model.transcribe(audio_chunk_path, word_timestamps=True)
                df = defaultdict(list)
                for segment in result["segments"]:
                    for word in segment["words"]:
                        df['word'].append(word['word'])
                        df['start'].append(round(word['start'] + i * chunk_length_ms / 1000, 2))
                        df['end'].append(round(word['end'] + i * chunk_length_ms / 1000, 2))
                pd.DataFrame(df).to_csv(transcription_out_path, index=False)

            update_task(task_id, {'progress': min(tasks[task_id]['progress'] + progress_step, 99)})

        update_task(task_id, {
            'progress': 100,
            'message': "Successfully processed the audio",
            'data': {
                "chunk_length": chunk_length_ms / 1000,
                "analysis_length": chunk_length_ms / 1000,
                "transcription_dir": transcription_out_dir
            },
        })

    except Exception as e:
        print("Error in analyze_asr: ", e)
        update_task(task_id, {
            'status': "error",
            'progress': 100,
            'message': f"Error in analyze_asr: {str(e)}",
            'data': {}
        })

@video_bp.route('/search_content', methods=['POST'])
def search_content():
    data = request.get_json()
    query = data.get("query", "")
    metadata = data.get("metadata", {})
    if not query:
        return jsonify({"status": "error", "message": "Query is required"}), 400

    task_id = str(int(time.time()))
    tasks[task_id] = {
        "task_type": "search_content",
        "status": "processing",
        "progress": 0,
        "message": "Processing the query",
        "data": []
    }
    result = overview_chain.process(query)
    if not result['success']:
        return jsonify({"status": "error", "message": "Failed to process the query"}), 400
    
    query = {
        'query': query,
        '4w1h': result['data']
    }
    # Start the background process
    thread = Thread(target=_search_content, args=(current_app._get_current_object(), task_id, query, metadata))
    thread.start()
    return jsonify({"status": "success", "task_id": task_id})

def _search_content(app, task_id, query, metadata):
    try:
        update_task(task_id, {'progress': 1})
        chunk_length = metadata.get('chunk_length', 120)
        analysis_length = metadata.get('analysis_length', 120)
        transcription_dir = metadata.get('transcription_dir', '')
        sliding_window = 0.5 * chunk_length
        start_time = 0
        search_results = []
        transcripts = sorted(glob.glob(f"{transcription_dir}/*.csv"))

        while start_time < len(transcripts) * chunk_length:
            end_time = start_time + analysis_length - 1
            start_chunk = transcripts[int(start_time / chunk_length)]
            end_chunk = transcripts[min(int(end_time / chunk_length), len(transcripts) - 1)]

            df = pd.read_csv(start_chunk)
            if start_chunk != end_chunk:
                next_df = pd.read_csv(end_chunk)
                df = pd.concat([df, next_df], ignore_index=True)

            analyze_df = df[(df['start'] >= start_time) & (df['end'] <= end_time)]
            content = analyze_df['word'].values.tolist()
            content_start_time = analyze_df['start'].values.tolist()
            content_end_time = analyze_df['end'].values.tolist()
            formatted_content = ''
            for i in range(len(content)):
                formatted_content += '(' + content[i] + ',' + str(content_start_time[i]) + ',' + str(content_end_time[i]) + ')'

            search_result = search_content_chain.process(formatted_content, query['4w1h']['What'])
            if search_result['success'] and 'None' not in str(search_result['data']['start_time']):
                search_results.append(search_result['data'])
            start_time += sliding_window

            progress = int((min(int(end_time / chunk_length)+1, len(transcripts) - 1) / len(transcripts)) * 90)
            update_task(task_id, {'progress': progress})

        ranked_results = search_content_chain.ranking(search_results, query['query'])
        update_task(task_id, {
            'progress': 99,
        })
        out_dir = os.path.dirname(transcription_dir)
        raw_video_path = os.path.join(out_dir, 'raw_video.mp4')
        video = VideoFileClip(raw_video_path)
        clip_dir = os.path.join(out_dir, 'clips')
        if os.path.exists(clip_dir):
            shutil.rmtree(clip_dir)
        os.makedirs(clip_dir, exist_ok=True)

        with app.app_context():
            ranked_data = ranked_results['data']
            for rank_data in ranked_data:
                start_t = int(float(rank_data['start_time']))
                end_t = int(float(rank_data['end_time']))
                video_clip = video.subclipped(start_t, end_t)
                video_clip_path = os.path.join(clip_dir, f"{start_t}_{end_t}.mp4")
                video_clip.write_videofile(video_clip_path, codec='libx264', audio_codec='aac')
                # Generate URL for the dynamically served downloads route
                relative_path = os.path.relpath(video_clip_path, './downloads').replace('\\', '/')
                rank_data['video_clip_path'] = url_for('video_routes.serve_downloads', filename=relative_path, _external=True)

            update_task(task_id, {
                'progress': 100,
                'message': "Successfully processed the query",
                'data': ranked_data
            })
    except Exception as e:
        print("Error in search_content: ", e)
        update_task(task_id, {
            'status': 'error',
            'progress': 100,
            'message': f"Error in search_content: {str(e)}",
            'data': []
        })

@video_bp.route('/downloads/<path:filename>', methods=['GET'])
def serve_downloads(filename):
    return send_from_directory('./downloads', filename)

@video_bp.route('/fetch', methods=['POST'])
def fetch_video():
    data = request.get_json()
    youtube_url = data.get('youtubeURL')

    if not youtube_url:
        return jsonify({"status": "error", "message": "YouTube URL is required"}), 400

    task_id = str(int(time.time()))
    with tasks_lock:
        tasks[task_id] = {
            "task_type": "fetch_video",
            "status": "processing",
            "progress": 0,
            "message": "Processing the video",
        }
    
    thread = Thread(target=_fetch_video, args=(youtube_url, task_id), daemon=True)
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def _fetch_video(youtube_url, task_id):
    try:
        yt = YouTube(youtube_url)
        video_url = yt.streams.first().url
        video_id = yt.video_id
        video_title = yt.title

        metadata = {
            "title": video_title,
            "id": video_id,
            "url": youtube_url
        }

        update_task(task_id, {
            "status": "completed",
            "progress": 100,
            "message": "Successfully processed the video",
            "data": metadata
        })
    except Exception as e:
        update_task(task_id, {
            "status": "error",
            "progress": 100,
            "message": f"Error fetching video: {str(e)}",
        })
