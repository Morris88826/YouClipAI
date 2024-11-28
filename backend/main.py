import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from libs.overview import OverviewTask


load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=256)

overview_chain = OverviewTask(global_llm)

if __name__ == "__main__":
    query = "I want to find the clip of Austin Reaves commenting about working out during Laker's media day."
    result = overview_chain.process(query)
    print(result)