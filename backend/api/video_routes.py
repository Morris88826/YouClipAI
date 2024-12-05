import os
import time
import json
import glob
import shutil
import whisper
import pandas as pd
from threading import Thread
from pytubefix import YouTube
from moviepy import VideoFileClip
from flask import Blueprint, request, jsonify, url_for, current_app, send_from_directory
from init import overview_chain, searcher, search_content_chain
from pydub import AudioSegment
from pydub.utils import make_chunks
from collections import defaultdict

video_bp  = Blueprint('video_routes', __name__, url_prefix='/api/videos')
download_dir='./downloads'
asr_model = whisper.load_model("turbo")

tasks = {}
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
            "metadata": task.get("metadata", None)
        })
    elif task['task_type'] == 'search_content':
        p = jsonify({
            "status": task["status"],
            "task_type": task["task_type"],
            "progress": task["progress"],
            "message": task["message"],
            "data": task.get("data", [])
        })
    elif task['task_type'] == 'advanced_search':
        p = jsonify({
            "status": task["status"],
            "task_type": task["task_type"],
            "progress": task["progress"],
            "message": task["message"],
            "data": task.get("data", [])
        })

    if task["status"] == "completed":
        tasks.pop(task_id)
    return p

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
                        "url": video_url
                    }
                }

                with open(os.path.join(video_out_dir, 'metadata.json'), 'w') as f:
                    json.dump(metadata, f)
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
            "task_type": "fetch_video",
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
        "metadata": None
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
            transcription_out_path = os.path.join(transcription_out_dir, f"{i:04d}.csv")
            if not os.path.exists(transcription_out_path):
                result = asr_model.transcribe(audio_chunk_path, word_timestamps=True)
                df = defaultdict(list)
                for segment in result["segments"]:
                    for word in segment["words"]:
                        df['word'].append(word['word'])
                        df['start'].append(round(word['start'] + i * chunk_length_ms / 1000, 2))
                        df['end'].append(round(word['end'] + i * chunk_length_ms / 1000, 2))
                df = pd.DataFrame(df)
                df.to_csv(transcription_out_path, index=False)
            tasks[task_id]['progress'] += progress_step

        tasks[task_id] = {
            "task_type": "analyze_asr",
            "status": "completed",
            "progress": 100,
            "message": "Successfully processed the audio",
            "metadata": {
                "chunk_length": chunk_length_ms / 1000,
                "analysis_length": chunk_length_ms / 1000,
                "transcription_dir": transcription_out_dir
            }
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
    # Start the background process
    thread = Thread(target=_search_content, args=(current_app._get_current_object(), task_id, query, metadata))
    thread.start()
    return jsonify({"status": "success", "task_id": task_id})

def _search_content(app, task_id, query, metadata):
    result = overview_chain.process(query)
    try:
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
                formatted_content += '(' + content[i] + ',' + str(content_start_time[i]) + ',' + str(content_end_time[i]) + ")"

            search_result = search_content_chain.process(formatted_content, result['data']['What'])
            if search_result['success'] and 'None' not in str(search_result['data']['start_time']):
                search_results.append(search_result['data'])
            start_time += sliding_window

            tasks[task_id]['progress'] = int((min(int(end_time / chunk_length), len(transcripts) - 1) / len(transcripts)) * 90)
        
        ranked_results = search_content_chain.ranking(search_results, query)
        
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
                video_clip.write_videofile(video_clip_path)
                # Generate URL for the dynamically served downloads route
                relative_path = os.path.relpath(video_clip_path, './downloads').replace('\\', '/')
                rank_data['video_clip_path'] = url_for('video_routes.serve_downloads', filename=relative_path, _external=True)

            tasks[task_id] = {
                "task_type": "search_content",
                "status": "completed",
                "progress": 100,
                "message": "Successfully processed the query",
                "data": ranked_data
            }

    except Exception as e:
        print(e)
        tasks[task_id] = {
            "task_type": "search_content",
            "status": "error",
            "progress": 100,
            "message": str(e),
            "data": []
        }
    return

@video_bp.route('/downloads/<path:filename>', methods=['GET'])
def serve_downloads(filename):
    return send_from_directory('./downloads', filename)

@video_bp.route('/advanced_search', methods=['POST'])
def advanced_search():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"status": "error", "message": "Query is required"}), 400

    task_id = str(int(time.time()))

    tasks[task_id] = {
        "task_type": "advanced_search",
        "status": "processing",
        "progress": 0,
        "message": "Processing the query",
        "data": []
    }

    # Start the background process
    thread = Thread(target=_advanced_search, args=(task_id, query))
    thread.start()

    return jsonify({"status": "success", "task_id": task_id})

def _advanced_search(task_id, query):
    try:
        result = overview_chain.process(query)
        if result['success']:
            search_query = overview_chain.generate_search_query(result['data'])
            print("Search Query: {} | Original Query: {}".format(search_query, query))
            search_result = searcher.search(search_query)
            if search_result['success']:
                videos = search_result['data']
                tasks[task_id] = {
                    "task_type": "advanced_search",
                    "status": "completed",
                    "progress": 100,
                    "message": "Successfully processed the query",
                    "data": videos
                }
            else:
                raise Exception("Failed to search for videos")
        else:
            raise Exception("Failed to process the query")
    except Exception as e:
        print(e)
        tasks[task_id] = {
            "task_type": "search_content",
            "status": "error",
            "progress": 100,
            "message": str(e),
            "data": []
        }
    return