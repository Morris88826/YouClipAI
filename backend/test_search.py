import os
import requests
from dotenv import load_dotenv
from pytubefix import YouTube

load_dotenv()
API_KEY = os.getenv('YouTube_API_KEY')
search_query = 'pokemon'
url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&q={search_query}&type=video&key={API_KEY}'

response = requests.get(url)
data = response.json()

out_dir = './downloads'
os.makedirs(out_dir, exist_ok=True)

for item in data['items']:
    video_id = item['id']['videoId']
    title = item['snippet']['title']
    print(f'Title: {title}, Video ID: {video_id}')

    # Download the video
    yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
    stream = yt.streams.first()
    stream.download(out_dir)
    print(f'Downloaded: {title}')
    
