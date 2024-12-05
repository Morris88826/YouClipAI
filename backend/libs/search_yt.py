import os
import sys
sys.path.append("..")
import requests
from dotenv import load_dotenv
from pytubefix import YouTube
from libs.overview import OverviewTask
from moviepy.video.io.VideoFileClip import VideoFileClip
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.output_parsers import StrOutputParser

post_process_prompt = PromptTemplate(
    input_variables=["search_results", "query"],
    template=(
        "You are an AI assistant tasked with analyzing which video might contains the user's query information based on the title\n\n"
        "Search Results: {search_results}\n"
        "Query: {query}\n\n"
        "You MUST return the ranked results in the following format:\n"
        "{{\n"
        "  \"ranked_results\": [\n"
        "    {{\n"
        "      \"video_id\": \"...\",\n"
        "      \"video_title\": \"...\",\n"
        "    }},\n"
        "    ...\n"
        "  ]\n"
        "}}"
    ),
)


class SearcYoutubeTask:
    def __init__(self, API_KEY, llm):
        self.API_KEY = API_KEY
        self.base_url = f'https://www.googleapis.com/youtube/v3/search'
        self.post_process_chain = RunnableSequence(post_process_prompt | llm | StrOutputParser())

    def search(self, search_query, max_results=5, video_duration='medium'):
        params = {
            'part': 'snippet',
            'type': 'video',
            'q': search_query,
            'key': self.API_KEY,
            'maxResults': max_results,
            'videoDuration': video_duration,
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
    
    def post_process_search(self, results, query):
        search_results = results['data']
        return self.post_process_chain.invoke({"search_results": search_results, "query": query})

if __name__ == "__main__":
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    YouTube_API_KEY = os.getenv('YouTube_API_KEY')
    global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=512)
    
    overview_chain = OverviewTask(global_llm)
    query = "I want to find the clip of Austin Reaves commenting about working out during Laker's media day 2024."
    result = overview_chain.process(query)
    
    
    if result['success']:
        search_query = overview_chain.generate_search_query(result['data'])
        print('Search Query:', search_query)
        search_task = SearcYoutubeTask(YouTube_API_KEY, global_llm)
        
        preliminary_result = search_task.search(search_query)
        print('Preliminary Search Results:')
        for item in preliminary_result['data']:
            print(f"Title: {item['title']}, Video ID: {item['video_id']}")
        print('-----------------------------------')
        post_processed_result = search_task.post_process_search(preliminary_result, search_query)
        print(post_processed_result)
