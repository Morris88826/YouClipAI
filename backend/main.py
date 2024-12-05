import os
import shutil
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from libs.overview import OverviewTask
from backend.libs.search_yt import SearcYoutubeTask


load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YouTube_API_KEY = os.getenv('YouTube_API_KEY')
global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=256)

overview_chain = OverviewTask(global_llm)
searcher = SearcYoutubeTask(YouTube_API_KEY)

if __name__ == "__main__":
    query = "I want to find the clip of Austin Reaves commenting about working out during Laker's media day 2024."
    result = overview_chain.process(query)
    
    
    if result['success']:
        search_query = overview_chain.generate_search_query(result['data'])
        search_result = searcher.search(search_query)
        
        if search_result['success']:
            # clean the downloads folder
            shutil.rmtree('./downloads') # TODO: uncomment this when releasing the code
            os.makedirs('./downloads', exist_ok=True)
            for item in search_result['data']:
                searcher.download_video(item, verbose=True)
                
