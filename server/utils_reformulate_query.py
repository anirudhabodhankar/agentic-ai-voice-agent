"""  
Module for interacting with Azure OpenAI to generate contexually correct query based on conversation history 
	new user query
"""  
import json
import os  
from typing import Any, Tuple

from jinja2 import Template  
from openai import AzureOpenAI  
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer(__name__)
  
# Load environment variables from .env file. Make sure this is already loaded from first import in main app file
 
# Initialize Azure OpenAI client  
client: AzureOpenAI = AzureOpenAI(  
    api_version="2025-01-01-preview",  
    api_key=os.getenv("AZURE_OPENAI_API_KEY", "NA"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "NA"),  
)  
  
  
def generate_system_message(device_id: str, device_language: str, chat_history: str) -> str:  
    """  
    Generates a system message using a Jinja2 template.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        device_language (str): The language setting of the device.  
        chat_history (str): The history of the user chat conversation.  
  
    Returns:  
        str: The rendered system message.  
    """  
    system_message_template: str = """  
    You are an intelligent assistant designed to process user queries based on conversation history.   
  
    **Task:** Given the conversation history and a new user query, generate a JSON object with the following two fields:  
    - `user_query`: The original user query in text format.  
    - `reformulated_query`: A refined or reformulated version of the user query that takes into account the provided conversation history for better context and understanding.  
    
   **Instructions:**   
    1. reformulate query only if needed based on chat history. Return the query as is if no reformulation is needed.  
    2. Give more weitage to context of last immediate user quesion or last immediate assistant response for reformulation.
  
    **Query reformulation examples **
    ##example 1  
    user: what is sum of my last two transactions  
    assistant: The total amount of your last two transactions is 1,450 (1,000 + 450).  
    user: what is my today's collection  
    assistant: The total amount collected today is 17,500.  
    user: and weekly  
    assistant: what is my weekly collection   
      
    ##example 2  
    user: what is my weekly collection  
    assistant: your total collection for the week is 85,000.  
    user: my device is not working properly  
    assistant: device not working properly  
  
    ##example 3  
    user: Device not working properly  
    assistant: Could you please specify the issue you're experiencing with your device? This will help me assist you better.  
    user: same transaction announced multiple times  
    assistant: device not working properly, duplication transaction announcement  
      
    ##example 4:   
    user : hello  
    assistant : Hello! How can I assist you with your device today?  
    user : how are you   
    assistant: I am doing great! Thanks for asking. How about you?  
  
    ##example 5:   
    user : hello  
    assistant : Hello  

    ##example 5:   
    user : Change device language to Marathi  
    assistant : The current device language is set to Kannada. Do you confirm that you want to change it to Marathi?  
    user : Yes
    assistant : Yes, Change device language to Marathi  


    **Input:**       
    - **Conversation History:**  
        {{ chat_history }}  
    - **The user device details**
        - Device ID: {{ device_id }}    
        - Device Language: {{ device_language }}    
    """  
    template: Template = Template(system_message_template)  
    rendered_message: str = template.render(  
        device_id=device_id,  
        device_language=device_language,  
        chat_history=chat_history  
    )  
    return rendered_message  
  
def get_text_completion(device_id: str, device_language: str, user_query: str, chat_history: str) -> str:  
    """  
    Generates a completion response for a user's query.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        device_language (str): The language setting of the device.  
        user_query (str): The user's input query.  
        chat_history (str): The history of the chat conversation.  
  
    Returns:  
        str: The assistant's response.  
    """  
    try:  
        # Generate system message  
        system_message: str = generate_system_message(  
            device_id=device_id,  
            device_language=device_language,  
            chat_history=chat_history  
        )  
  
        # Prepare the messages structure for the chat completion API  
        messages: list[dict[str, Any]] = [  
            {"role": "system", "content": system_message},  
            {"role": "user", "content": user_query},  
        ]  
  
        # Call Azure OpenAI chat completions API  
        response = client.chat.completions.create(  
            model="gpt-4o-mini",  # Replace with your Azure deployment name  
            messages=messages,  
            temperature=1.0,  
            max_tokens=50  
        )  
  
        # Extract response and return content  
        assistant_message: str = response.choices[0].message.content  
        return assistant_message  
  
    except Exception as e:  
        console_logger.error(f"Error in get_completion: {e}")  
        return ""
  
  
def get_audio_completion(device_id: str, device_language: str, encoded_string: str, chat_history: str) -> Tuple[str, str]:  
    """  
    Generates a completion response from an audio-encoded user input.  
  
    Args:  
        device_id (str): The unique identifier of the device.  
        device_language (str): The language setting of the device.  
        encoded_string (str): The base64-encoded audio input.  
        chat_history (str): The history of the chat conversation.  
  
    Returns:  
        str: The assistant's response.  
    """  
    console_logger.debug(f'get_audio_completion, device_id: {device_id}')
    try:  
    # Generate system message  
        system_message: str = generate_system_message(  
            device_id=device_id,  
            device_language=device_language,  
            chat_history=chat_history  
        )  

        # Prepare the messages structure for the chat completion API with audio input  
        messages: list[dict[str, Any]] = [  
            {"role": "system", "content": system_message},  
            {"role": "user", "content": [  
                {   
                    "type": "input_audio",   
                    "input_audio": {   
                        "data": encoded_string,   
                        "format": "wav"   
                    }   
                }  
            ]},  
        ]  

        console_logger.info(f'get_audio_completion, sending call to gpt for reformulation')
        # Call Azure OpenAI chat completions API with audio modality  
        response = client.chat.completions.create(  
            model="gpt-4o-audio-preview",  
            modalities=["text"],  
            messages=messages,  
            temperature=1.0,  
            max_tokens=50  
        )  

        console_logger.debug(f'get_audio_completion, got response from gpt: {response}')    
        # Extract response and return content  
        assistant_message: str = response.choices[0].message.content
        first_brace = assistant_message.find('{')  
        last_brace = assistant_message.rfind('}')  

        data = ""
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:  
            potential_json = assistant_message[first_brace:last_brace+1]  
            data = json.loads(potential_json)  
            console_logger.debug(f'get_audio_completion, data: {data}')

        return data["user_query"], data["reformulated_query"]
  
    except Exception as e:  
        console_logger.error(f"Error in get_completion_from_audio: {e}")  
        return ""  