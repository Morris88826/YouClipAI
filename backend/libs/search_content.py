import os
import sys
import glob
import numpy as np
import argparse
import pandas as pd
sys.path.append("..")
from libs.overview import OverviewTask
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.output_parsers import StrOutputParser

search_prompt = PromptTemplate(
    input_variables=["transcript", "start_time", "What"],
    template=(
        "You are an AI assistant specialized in extracting relevant sections from transcripts based on the 'What' information provided in the context of a 4W1H framework (Who, What, When, Where, Why, and How). \n"
        "Instructions:"
        "1. Identify and extract the section that CONTAINS information related to the 'What' provided.\n"
        "2. If no relevant section is found, return 'None' for all fields.\n"
        "3. You MUST ensure that the extracted content is the LONGEST continuous section that covers the 'What' information.\n"
        "Transcript [(word, start_time, end_time), ...]: {transcript}\n"
        "What (Information to extract): {What}\n"
        
        "You MUST return in the following format:\n"
        "{{\n"
        "  \"content\": \"The relevant section from the transcript or 'None' if no match.\",\n"
        "  \"info\": \"Explanation or context of the relevant section or 'None' if no match.\",\n"
        "  \"start_time\": \"The start time of the relevant section or 'None' if no match.\",\n"
        "  \"end_time\": \"The end time of the relevant section or 'None' if no match.\"\n"
        "}}"
    ),
)

response_schemas = [
    ResponseSchema(name="content", description="The content extracted from the transcript."),
    ResponseSchema(name="info", description="The extracted information based on the 'What' information in a 4W1H framework."),
    ResponseSchema(name="start_time", description="The start time of the extracted content."),
    ResponseSchema(name="end_time", description="The end time of the extracted content."),
]
search_output_parser = StructuredOutputParser(response_schemas=response_schemas)

ranking_prompt = PromptTemplate(
    input_variables=["search_results", "query"],
    template=(
        "You are an AI assistant tasked with analyzing, merging, and ranking search results based on their relevance to a given query.\n\n"
        "Instructions:\n"
        "1. Identify overlapping or closely related sections:\n"
        "   - Two sections are considered overlapping if their time ranges intersect or if the end time of one section is within 5 seconds of the start time of another.\n"
        "   - Two sections are considered closely related if their content discusses the same topic or has thematic similarity to the query.\n"
        "   - Merge sections only if they meet both criteria: overlapping time ranges and thematic similarity.\n"
        "2. Rank the merged sections based on their relevance to the query:\n"
        "   - Prioritize sections that directly address the query.\n"
        "   - Rank higher sections that are more specific, unique, and detailed in their relevance to the query.\n"
        "3. The MOST relevant section should be at the start of the list.\n"
        
        "Search Results: {search_results}\n"
        "Query: {query}\n\n"
        
        "You MUST return the ranked results in the following format:\n"
        "{{\n"
        "  \"ranked_results\": [\n"
        "    {{\n"
        "      \"start_time\": \"Earliest start time of the merged section, MUST be in float\",\n"
        "      \"end_time\": \"Latest end time of the merged section, MUST be in float\"\n"
        "    }},\n"
        "    ...\n"
        "  ]\n"
        "}}"
    ),
)

response_schemas = [
    ResponseSchema(name="ranked_results", description="The ranked search results based on relevance to the query."),
]
ranking_output_parser = StructuredOutputParser(response_schemas=response_schemas)

class SearchContentTask:
    def __init__(self, llm):
        self.llm = llm
        self.chain = RunnableSequence(search_prompt | llm | search_output_parser)
        self.ranking_chain = RunnableSequence(ranking_prompt | llm | ranking_output_parser)

    def process(self, transcript, What, num_tries=5):
        for _ in range(num_tries):
            try:
                data = self._process(transcript, What)
                return {
                    'success': True,
                    'data': data,
                    'message': 'Successfully processed the query.',
                }
            except Exception as e:
                pass
        return {
            'success': False,
            'error': {
                'type': 'ProcessingError',
                'message': 'Failed to process the query.',
            }
        }
    
    def _process(self, transcript, What):   
        result = self.chain.invoke({"transcript": transcript, "What": What})
        return result
    
    def ranking(self, search_results, query, num_tries=5):
        for _ in range(num_tries):
            try:
                result = self.ranking_chain.invoke({"search_results": search_results, "query": query})
                result = result['ranked_results']
                return {
                    'success': True,
                    'data': result,
                    'message': 'Successfully processed the query.',
                }
            except Exception as e:
                print(e)
                pass    
        return {
            'success': False,
            'error': {
                'type': 'ProcessingError',
                'message': 'Failed to process the query.',
            }
        }
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', default="../downloads/cNXxqE7hs9U/transcriptions", help='Path to the input transcript directory')
    parser.add_argument('-q', '--query', default="I want to find the clip of Austin Reaves commenting about posting working out in gym during Laker's media day 2024.", help='Query to search for in the transcripts')
    parser.add_argument('--chunk_length', type=int, default=120, help='Length of the audio chunks in seconds')
    parser.add_argument('--analysis_length', type=int, default=120, help='Length of the audio analysis in seconds')
    args = parser.parse_args()    

    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    global_llm = ChatOpenAI(name="gpt-4o-mini", temperature=0, max_tokens=256)

    transcripts = sorted(glob.glob(f"{args.input}/*.csv"))
    print(f"Found {len(transcripts)} transcripts")


    query = args.query
    overview_chain = OverviewTask(global_llm)
    result = overview_chain.process(query)
    search_chain = SearchContentTask(global_llm)

    if result['success']:
        chunk_length = args.chunk_length
        analysis_length = args.analysis_length
        sliding_window = 0.5 * chunk_length
        start_time = 0
        search_results = []
        while start_time < len(transcripts) * chunk_length:
            end_time = start_time + analysis_length - 1
            print(f"Analyzing from {start_time} to {end_time}")
            
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
  
            search_result = search_chain.process(formatted_content, result['data']['What'])
            if search_result['success'] and 'None' not in str(search_result['data']['start_time']):
                search_results.append(search_result['data'])
            start_time += sliding_window
        
        ranked_results = search_chain.ranking(search_results, query)
        if ranked_results['success']:
            ranked_data = ranked_results['data']
            for rank_data in ranked_data:
                print(rank_data)
            # print("Top Ranked Results:")
            # for i, rank in enumerate(ranked_data):
            #     print(search_results[rank])
            #     print("---------------------------------------------------------")

        # for i, transcript in enumerate(transcripts):
        #     if i != len(transcripts) - 1:
        #         next_transcript = transcripts[i+1]
                
        #     df = pd.read_csv(transcript)
        #     content = df['word'].values.tolist()
        #     content = '|'.join(content)
        #     start_time = df['start'].values.tolist()
        #     start_time = '|'.join([str(x) for x in start_time])

        #     search_result = search_chain.process(content, start_time, result['data']['What'])
            
        #     if search_result['success']:
        #         print(f"Transcript {i+1} - {transcript}")
        #         print(f"Search Result: {search_result['data']['content']} | Info: {search_result['data']['info']} | Start Time: {search_result['data']['start_time']} | End Time: {search_result['data']['end_time']}")
        #         print("---------------------------------------------------------")