import os
import requests
from dotenv import load_dotenv
from pytubefix import YouTube
from moviepy.video.io.VideoFileClip import VideoFileClip

class SearchTask:
    def __init__(self, API_KEY):
        self.API_KEY = API_KEY
        self.base_url = f'https://www.googleapis.com/youtube/v3/search'


    def search(self, search_query, max_results=5, video_duration='medium'):
        params = {
            'part': 'snippet',
            'type': 'video',
            'q': search_query,
            'key': self.API_KEY,
            'maxResults': max_results,
            'videoDuration': video_duration
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            result = response.json()
            parsed_result = []
            for item in result['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                parsed_result.append({
                    'title': title,
                    'video_id': video_id,
                    'timestamp': item['snippet']['publishedAt'],
                })
            return {
                'success': True,
                'data': parsed_result,
                'message': 'Successfully fetched the search results.',
            }
        else:
            raise {
                'success': False,
                'error': {
                    'type': 'APIError',
                    'message': 'Failed to fetch the search results.',
                }
            }

    def download_video(self, item, out_dir='./downloads', verbose=False, audio=True):
        video_title = item['title']
        video_id = item['video_id']
        if verbose:
            print(f"Downloading video: {video_title} ...")
        video_id = item['video_id']
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        stream = yt.streams.first()
        video_out_path = stream.download(out_dir)

        if audio:
            audio_out_dir = os.path.join(out_dir, 'audio')
            os.makedirs(audio_out_dir, exist_ok=True)
            audio_out_path = os.path.join(audio_out_dir, f'{video_title}.wav')
            video = VideoFileClip(video_out_path)
            audio = video.audio
            audio.write_audiofile(audio_out_path)
            video.close()
            audio.close()
        return 

if __name__ == "__main__":
    search_query = 'austin reaves media day 2024'
    load_dotenv()
    YouTube_API_KEY = os.getenv('YouTube_API_KEY')
    search_task = SearchTask(YouTube_API_KEY)
    data = search_task.search(search_query)
    print(data)