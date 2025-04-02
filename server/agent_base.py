import dotenv
from pathlib import Path 
dotenv.load_dotenv(dotenv_path=Path(__file__).parent.parent / 'server' / '.env' )

from typing import Tuple, Any, Optional, AsyncGenerator
  
from server import utils_langchain
from server import utils_db  
from server import utils_voice_llm  
from server import utils_logger
from server import utils_speech
console_logger, console_tracer = utils_logger.get_logger_tracer()

from opentelemetry.instrumentation.langchain import LangchainInstrumentor
LangchainInstrumentor().instrument()   

@console_tracer.start_as_current_span("fetch_device_session_details")
def fetch_device_session_details(device_id: str, user_input: str) -> Tuple[str, Any, Any]:  
    """  
    Retrieves session and conversation details for a given device.  
  
    Args:  
        device_id (str): The unique identifier for the device.  
        user_input (str): The user's input or query.  
  
    Returns:  
        Tuple[str, Any, Any]: A tuple containing session ID, conversation object, and chat history.  
    """  
    console_logger.debug(f'Getting conversation for device_id: {device_id}')  
    session_id: str = utils_db.get_session_id(device_id)        
    conversation: Any = utils_db.get_conversation_or_create_new(  
        session_id=session_id,  
        device_id=device_id,  
        title=user_input  
    )  

    console_logger.debug(f'Getting langchain conversation for conversation: {session_id}')  
      
    chat_history: Any = utils_db.get_langchain_chat_from_conversation(conversation)  
    console_logger.debug(f'Chat history is - {chat_history}')  
      
    return session_id, conversation, chat_history  


async def get_conversation_response_streaming(  
    device_id: str,  
    user_input: Optional[str] = None,  
    user_audio_input: Optional[str] = None  
)  -> AsyncGenerator[bytes, None]:  
    """  
    Processes user input (text or audio) and generates a streaming response from the conversation.  
  
    Args:  
        device_id (str): The unique identifier for the device.  
        user_input (Optional[str], optional): The user's text input. Defaults to None.  
        user_audio_input (Optional[str], optional): b64encoded utf 8 sring  - base64.b64encode(wav_reader.read()).decode('utf-8')
  
    Returns:  
        str: The assistant's text response.  
    """  
    with console_tracer.start_as_current_span("get_conversation_response_streaming") as span:
        first_audio_chunk_span = console_tracer.start_span("network_first_audio_chunk")
        console_logger.warning(f'get_conversation_response_streaming called with device_id: {device_id}')  
        transcript = ""
    
        session_id, conversation, chat_history = fetch_device_session_details(device_id, user_input=user_input)  

        device_info = utils_db.get_device_info(device_id)
        
        requery: str = ""  
        if user_input:  
            requery = user_input
        elif user_audio_input:  
            transcript = utils_speech.speech_to_text_from_base64(user_audio_input)
            requery = transcript
    
        console_logger.info(f'Executing the query: {requery}')  
    
        audio_generator: utils_voice_llm.TextToGPTAudioStreamGenerator = utils_voice_llm.TextToGPTAudioStreamGenerator()  
        total_audio_size: int = 0  
        first_audio_chunk: bool = True
    
        agent_args = {
            "input": requery,   
            "device_id": device_id,  
            "session_id": conversation["id"], 
            "user_language": device_info["language"],
            "device_info": device_info,
            "chat_history": chat_history  
        }

        tool_filter_message = ""
        if(len(chat_history) >= 2):
            tool_filter_message += chat_history[-2]["role"] + ": " + chat_history[-2]["content"] + "\n"
            tool_filter_message += chat_history[-1]["role"] + ": " + chat_history[-1]["content"] + "\n"
        
        tool_filter_message += f"human: {requery}"
        # Initialize Agent Executor  
        agent_executor = utils_langchain.get_agent_executor(tool_filter_message) 
        tool_names = [structured_tool.name for structured_tool in agent_executor.tools] 
        
        total_audtio_chunks_on_network = 0;
        console_logger.debug(f'Agent args: {agent_args}')
        try:  
            async for audio_chunk in audio_generator.generate_audio_chunks(  
                agent_executor,  
                agent_args
            ):  
                if first_audio_chunk:  
                    first_audio_chunk_span.end()
                    console_logger.info("First audio chunk sent back over network of size: %s bytes", len(audio_chunk)) 
                    first_audio_chunk = False
                total_audio_size += len(audio_chunk)  
                total_audtio_chunks_on_network += 1
                yield audio_chunk
        except Exception as e:  
            console_logger.error(f"Error generating audio chunks: {e}")  
    
        text_response: str = audio_generator.get_full_response()  
        utils_db.add_messages_to_conversation(  
            conversation,  
            [  
                {"role": "user", "content": transcript},  
                {"role": "requery", "content": requery},  
                {"role": "tools", "content": tool_names},
                {"role": "assistant", "content": text_response}  
            ]  
        )  
    
        console_logger.info(f'Full response: {text_response}')  
        console_logger.info(f'Total audio chunks on network: {total_audtio_chunks_on_network}')  
        console_logger.info(f'Total audio size in KB: {total_audio_size / 1024:.2f} KB')  