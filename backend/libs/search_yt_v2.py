import os
import sys
sys.path.append("..")
import requests
import time
from dotenv import load_dotenv
from pytubefix import YouTube
from libs.overview import OverviewTask
from moviepy.video.io.VideoFileClip import VideoFileClip
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.output_parsers import StrOutputParser
from pytubefix import YouTube
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

postprocess_prompt = PromptTemplate(
    input_variables=["search_results", "query"],
    template=(
        "You are an AI assistant tasked with analyzing which video might contains the user's query information based on the title\n\n"
        "Search Results: {search_results}\n"
        "Query: {query}\n\n"
        "You MUST return the ranked results in the following format:\n"
        "{{\n"
        "  \"ranked_results\": [\n"
        "    {{\n"
        "      \"id\": \"...\",\n"
        "      \"title\": \"...\",\n"
        "      \"url\": \"...\n"
        "    }},\n"
        "    ...\n"
        "  ]\n"
        "}}"
    ),
)

response_schemas = [
    ResponseSchema(name="ranked_results", description="The ranked search results based on the user's query."),
]
postprocess_parser = StructuredOutputParser(response_schemas=response_schemas)


class SearcYoutubeTask:
    def __init__(self, llm):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # Ensure GUI is off
        self.chrome_options.add_argument("--disable-gpu") 
        self.chrome_options.add_argument("--window-size=1920x1080")  

        self.base_url = "https://www.youtube.com/"
        self.postprocess_chain = RunnableSequence(postprocess_prompt | llm | postprocess_parser)

        self.duration_map = {
            'short': 'PT4M',     # Videos shorter than 4 minutes
            'medium': 'PT4M-PT20M',  # Videos between 4 minutes and 20 minutes
            'long': 'PT20M-PT1H',  # Videos between 20 minutes and 1 hour
        }

    def search(self, search_query, max_results=20):
        driver = webdriver.Chrome(options=self.chrome_options)
        driver.get(self.base_url)
        # Wait for the search box to load
        wait = WebDriverWait(driver, 10)
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "search_query")))

        search_box = driver.find_element(By.NAME, "search_query")
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)

        results = []
        videos = driver.find_elements(By.XPATH, '//ytd-video-renderer')[:max_results]
        for video in videos:
            try:
                title_elem = video.find_element(By.XPATH, './/a[@id="video-title"]')
                title = title_elem.text
                url = title_elem.get_attribute("href")
                
                yt = YouTube(url)
                video_id = yt.video_id
                url = yt.watch_url
                duration = yt.length

                print(f"Title: {title}, URL: {url}, Duration: {duration}")

                if duration < 240 or duration > 1200:
                    continue

                results.append({
                    'id': video_id,
                    'title': title,
                    'url': url,
                })
            except Exception as e:
                print(f"Error processing video: {e}")
                continue

        driver.quit()
        return {
            'success': True,
            'data': results,
            'message': 'Successfully fetched the search results.',
        }


    def download_video(self, video, out_dir='./downloads', verbose=False, audio=True):
        video_id = video['id']
        video_title = video['title']
        if verbose:
            print(f"Downloading video: {video_title} ...")
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
    
    def postprocess(self, results, query, num_tries=5):
        search_results = results['data']
        for _ in range(num_tries):
            try: 
                results = self.postprocess_chain.invoke({"search_results": search_results, "query": query})
                return {
                    'success': True,
                    'data': results['ranked_results'],
                }
            except Exception as e:
                print(f"Error processing search results: {e}")
        return {
            'success': False,
            'error': {
                'type': 'ProcessingError',
                'message': 'Failed to process the search results.',
            }
        }

if __name__ == "__main__":
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=512)
    
    overview_chain = OverviewTask(global_llm)
    search_task = SearcYoutubeTask(global_llm)
    query = "I want to find the clip of Austin Reaves commenting about working out during Laker's media day 2024."
    result = overview_chain.process(query)

    if result['success']:
        search_query = overview_chain.generate_search_query(result['data'])

        preliminary_result = search_task.search(search_query)
        print('Preliminary Search Results:')
        for item in preliminary_result['data']:
            print(f"Title: {item['title']}, Video ID: {item['video_id']}")
        print('-----------------------------------')
        postprocessed_result = search_task.postprocess(preliminary_result, search_query)
        print('Post-Processed Search Results:')
        for item in postprocessed_result['data']:
            print(f"Title: {item['video_title']}, Video ID: {item['video_id']}")
