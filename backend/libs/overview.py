import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.output_parsers import StrOutputParser

overview_prompt = PromptTemplate(
    input_variables=["query"],
    template=(
        "Analyze the query and extract the relevant information according to the 4W1H framework (Who, What, When, Where, How).\n"
        "Query: {query}\n"
        "You MUST provide a response for each category in the following format, even if it is blank.\n"
        "Respond in this JSON format:\n"
        "{{\n"
        "  \"Who\": \"...\",\n"
        "  \"What\": \"...\",\n"
        "  \"When\": \"...\",\n"
        "  \"Where\": \"...\",\n"
        "  \"How\": \"...\"\n"
        "}}"
    ),
)
response_schemas = [
    ResponseSchema(name="Who", description="The person or entity involved in the query."),
    ResponseSchema(name="What", description="The action or event described in the query."),
    ResponseSchema(name="When", description="The time or date mentioned in the query."),
    ResponseSchema(name="Where", description="The location or place mentioned in the query."),
    ResponseSchema(name="How", description="The method or process described in the query."),
]
overview_output_parser = StructuredOutputParser(response_schemas=response_schemas)

generate_search_query = PromptTemplate(
    input_variables=["Who", "What", "When", "Where", "How"],
    template=(
        "Generate an optimized YouTube search query based on the extracted 4W1H framework. "
        "The query should prioritize relevance and include important keywords to accurately target YouTube's search algorithm. "
        "Use concise, descriptive terms and consider phrases that users would commonly search for on YouTube.\n"
        "\n"
        "Extracted Information:\n"
        "Who: {Who}\n"
        "What: {What}\n"
        "When: {When}\n"
        "Where: {Where}\n"
        "How: {How}\n"
        "\n"
        "Guidelines for the query:\n"
        "1. Include key terms and phrases relevant to the extracted information.\n"
        "2. Use quotation marks for IMPORTANT content (e.g., \"media day\").\n"
        "3. Incorporate the year if applicable to ensure results are time-specific.\n"
        "\n"
        "Provide a single, well-crafted search query that can be used directly in YouTube.\n"
        "ONLY return the search query as the response."
    ),
)

class OverviewTask:
    def __init__(self, llm):
        self.llm = llm
        self.chain = RunnableSequence(overview_prompt | llm | overview_output_parser)
        self.generate_search_chain = RunnableSequence(generate_search_query | llm | StrOutputParser())

    def process(self, query, num_tries=5):
        for _ in range(num_tries):
            try:
                data = self._process(query)
                return {
                    'success': True,
                    'data': data,
                    'message': 'Successfully processed the query.',
                }
            except Exception as e:
                print(e)
        return {
            'success': False,
            'error': {
                'type': 'ProcessingError',
                'message': 'Failed to process the query.',
            }
        }
    
    def _process(self, query):
        result = self.chain.invoke({"query": query})
        return result
    
    def generate_search_query(self, data):
        result = self.generate_search_chain.invoke({"Who": data["Who"], "What": data["What"], "When": data["When"], "Where": data["Where"], "How": data["How"]})
        return result
