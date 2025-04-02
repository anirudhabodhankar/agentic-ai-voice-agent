
#python -m bot.agent_text 
import asyncio  
import threading  
from bot import agent_proxy

from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

def print_system_threads():  
    """  
    Logs details of all active threads.  
    """  
    console_logger.debug("---- Active Threads ----")  
    for thread in threading.enumerate():  
        console_logger.debug(f"Thread name: {thread.name}, Daemon: {thread.daemon}, Alive: {thread.is_alive()}")  
    console_logger.debug("------------------------")  

async def start_conversation(device_id: str):  
    """  
    Asynchronously handles user input and processes it.  
    """  
    while True:  
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Enter text (type 'q' to exit): ")  
        console_logger.debug(f"User input received: {user_input}")  
  
        if user_input.lower() == 'q':  
            console_logger.info("User requested to exit. Terminating...")  
            break  
  
        try:  
            console_logger.debug("Initiating get_conversation_response_streaming...")  
            proxy = agent_proxy.AgentProxy()
            response = await proxy.generate_audio_response(  
                device_id=device_id,  
                user_input=user_input,  
                user_audio_file=None  
            )  
            console_logger.debug(f"Received response: {response}")  
        except Exception as e:  
            console_logger.exception(f"Exception during get_conversation_response_streaming: {e}")  
  
        
def start_conversation_thread(device_id: str):  
    """  
    Sets up and runs the asynchronous event loop.  
    """  
    try:  
        console_logger.info("Starting chat stream...")  
        asyncio.run(start_conversation(device_id))  
    except RuntimeError as e:  
        console_logger.exception(f"RuntimeError encountered: {e}")  
    except Exception as e:  
        console_logger.exception(f"Unexpected exception: {e}")  
    finally:  
        console_logger.info("Chat stream terminated.")  
        print_system_threads()  


if __name__ == "__main__":  
    device_id = "864068071000003"  
    start_conversation_thread(device_id=device_id)  
    console_logger.info("Program has exited.")  
    # After processing, print active threads  
    

