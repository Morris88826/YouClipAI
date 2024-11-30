import os
from langchain_openai import ChatOpenAI
from libs.overview import OverviewTask
from libs.search import SearchTask
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YouTube_API_KEY = os.getenv('YouTube_API_KEY')
global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=256)

overview_chain = OverviewTask(global_llm)
searcher = SearchTask(YouTube_API_KEY)