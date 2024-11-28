import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


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

class OverviewTask:
    def __init__(self, llm):
        self.llm = llm
        self.chain = RunnableSequence(overview_prompt | llm | overview_output_parser)

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
    
    
    