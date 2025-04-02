import os
import dotenv
import requests
import json
dotenv.load_dotenv(dotenv_path="./server/.env" )
from typing import Optional
import io
from server import utils_logger
import base64
from bot.utills_audio_player import AudioPlayer 
import pydub
import traceback 
import websockets
import asyncio
from opentelemetry import context as context_api

is_single_app = True if os.getenv("IS_SINGLE_APP", "True").lower() == "true" else False
server_url: str = os.getenv("SERVER_URL", "http://localhost:8000/voice_chat_stream")  
audio_input_format: str = os.getenv("AUDIO_INPUT_FORMAT", "wav") 
audio_input_format = "wav" if is_single_app else audio_input_format
server_url = f'{server_url}_{audio_input_format}'

console_logger, console_tracer = utils_logger.get_logger_tracer()

if is_single_app:
    from server import main
    from server import utils_speech

console_logger.info(f"Is single app: {is_single_app}")



headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

def create_amr_byte_array(input_file_name, output_file_name):
    console_logger.debug(f'converting input file {input_file_name} to amr format')
    audio = pydub.AudioSegment.from_file(input_file_name, format='wav')
    buffer = io.BytesIO()
    buffer.name = output_file_name
    audio.set_frame_rate(8000).set_channels(1).export(buffer, format='amr')
    buffer.seek(0)
    audio_bytes = buffer.getvalue()

    buffer.close()
    return audio_bytes

def play_filler_music(ap: AudioPlayer, count: int) -> None:  
    """  
    Plays filler music by adding audio chunks to the provided AudioPlayer instance.  
  
    Args:  
        ap (AudioPlayer): An instance of AudioPlayer to manage audio playback.  
    """  
    audio_file_path: str = "audio\\radar_2.wav"  
    try:  
        with open(audio_file_path, "rb") as f:  
            audio_bytes: bytes = f.read()  
            for i in range(count):
                ap.add_audio([audio_bytes])  
            
    except FileNotFoundError:  
        console_logger.error(f"Audio file not found: {audio_file_path}")  
    except Exception as e:  
        console_logger.error(f"Error playing filler music: {e}")  
        
def get_all_pairs(input, previous_partial_input):
    try:
        input = input.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return [input], ""
    
    input = previous_partial_input + input
    pairs = []
    start = 0
    while True:
        start = input.find('{', start)
        if start == -1:
            break
        end = input.find('}', start)
        if end == -1:
            break
        pairs.append(input[start:end+1])
        start = end + 1
    
    # The remaining part of the string is the partial pair, if any
    partial_pair = input[start:] if input.find('{', start) != -1 else ''
    
    return pairs, partial_pair

class AgentProxy :
    @console_tracer.start_as_current_span("AgentProxy - __init__")
    def __init__(self):
        self.total_audio_size: int = 0  
        self.total_audio_chunks: int = 0  
        self.total_packets: int = 0
        self.total_data_size: int = 0
        self.is_first_chunk = True
        self.encoded_string = None
        self.last_chunk = ""

        self.ap: AudioPlayer = AudioPlayer(parent_context=context_api.get_current())  
        console_logger.info(f"Audio input format: {audio_input_format}")
        console_logger.info(f"Server url: {server_url}")

    @console_tracer.start_as_current_span("process_audio_chunk")
    def process_audio_chunk(self,audio_chunk: bytes) -> None:
        self.total_data_size += len(audio_chunk)  
        self.total_packets += 1
        chunks, self.last_chunk = get_all_pairs(audio_chunk, self.last_chunk)
        if self.is_first_chunk and len(chunks) > 0:
            self.is_first_chunk = False
            console_logger.info(f"Received First audio chunk of size: {len(chunks[0])}")
        for chunk in chunks:
            query_response = json.loads(chunk)
            if(query_response["type"] == "audio"):
                audio = base64.b64decode(query_response["audio"])
                self.total_audio_size += len(audio)
                self.total_audio_chunks += 1
                self.ap.add_audio([audio])

    @console_tracer.start_as_current_span("generate_audio_response")
    async def generate_audio_response(self,
        device_id: str,  
        user_input: Optional[str] = "",  
        user_audio_file: Optional[str] = None  
    ):
        console_logger.info(f"Sending user for device id : {device_id}, user input: {user_input}, user audio file: {user_audio_file}")        
        play_filler_music(self.ap, 1)         

        encoded_string = ""
        try:
            if(user_audio_file):  
                audio_bytes = None
                if audio_input_format == "amr":
                    audio_bytes = create_amr_byte_array(user_audio_file, "temp.amr")
                else:
                    with open(user_audio_file, "rb") as wav_reader:  
                        audio_bytes = wav_reader.read()
                encoded_string = base64.b64encode(audio_bytes).decode('utf-8')

            if(is_single_app):
                query_input = main.QueryInput(device_id=device_id, user_input=user_input, user_audio_input=encoded_string)
                console_logger.info(f"Received User input: {query_input.user_input}")
                async for audio_chunk in main.get_audio_stream_base64( query_input=query_input, type=audio_input_format):
                    self.process_audio_chunk(audio_chunk) 

            else:
                request_paylaod = {
                    "device_id": device_id,
                    "user_input": user_input,
                    #"user_input": "",
                    "user_audio_input": encoded_string
                }   

                with requests.get(url=server_url, stream=True, headers=headers, json=request_paylaod) as response:
                    for audio_chunk in response.iter_content(chunk_size=1024):                                
                        self.process_audio_chunk(audio_chunk) 

        except FileNotFoundError:  
            console_logger.error(f"Audio input file not found: {user_audio_file}")
        except Exception as e:  
            traceback.print_exc() 
            console_logger.error(f"Error generating audio chunks: {e}")

        console_logger.info(f'Total data received in KB: {self.total_data_size / 1024:.2f} KB')  
        console_logger.info(f"Total packets received: {self.total_packets}")
        console_logger.info(f'Total audio size received in KB: {self.total_audio_size / 1024:.2f} KB')  
        console_logger.info(f"Total audio chunks received: {self.total_audio_chunks}")
        self.ap.add_audio_complete()  
        self.ap.wait_for_completion()  


class AgentProxySocketsSingleApp:
    @console_tracer.start_as_current_span("AgentProxySocketsSingleApp - __init__")
    def __init__(self, device_id: str = None):
        self.device_id = device_id

        self.total_audio_size_sent: int = 0  
        self.total_audio_chunks_sent: int = 0  

        self.total_audio_size: int = 0  
        self.total_audio_chunks: int = 0  

        self.is_first_chunk = True
        self.last_chunk = ""

        self.streaming_stt = utils_speech.StreamingSTT(parent_context=context_api.get_current())
        self.streaming_stt.create_stream()
    
    async def add_audio(self, frames):
        self.total_audio_chunks_sent += 1
        for frame in frames:
            self.total_audio_size_sent += len(frame)
           
        self.streaming_stt.add_audio(frames)
    
    async def add_audio_complete(self):
        self.streaming_stt.add_audio_complete()

    @console_tracer.start_as_current_span("AgentProxySocketsSingleApp - generate_audio_response")
    async def generate_audio_response(self):
        console_logger.info(f"Sending user for device id : {self.device_id}")       
        self.streaming_stt.add_audio_complete()  # must be done to signal the end of stream 
        ap: AudioPlayer = AudioPlayer(parent_context=context_api.get_current())  
        play_filler_music(ap, 1)         

        try:
            async for audio_chunk in main.get_audio_stream(device_id=self.device_id, streaming_stt=self.streaming_stt):
                if self.is_first_chunk:
                    self.is_first_chunk = False
                    console_logger.info(f"Received First audio chunk of size: {len(audio_chunk)/ 1024:.2f} KB")  

                self.total_audio_size += len(audio_chunk)
                self.total_audio_chunks += 1
                ap.add_audio([audio_chunk])

        except Exception as e:  
            traceback.print_exc() 
            console_logger.error(f"Error generating audio chunks: {e}")

        console_logger.info(f'Total audio size sent in KB: {self.total_audio_size_sent / 1024:.2f} KB')  
        console_logger.info(f"Total audio chunks sent: {self.total_audio_chunks}")

        console_logger.info(f'Total audio size received in KB: {self.total_audio_size / 1024:.2f} KB')  
        console_logger.info(f"Total audio chunks received: {self.total_audio_chunks}")
        ap.add_audio_complete()  
        ap.wait_for_completion()  

class AgentProxySockets:
    @console_tracer.start_as_current_span("AgentProxySockets - __init__")
    def __init__(self, device_id: str = None):
        self.device_id = device_id

        self.total_audio_size_sent: int = 0  
        self.total_audio_chunks_sent: int = 0  

        self.total_audio_size: int = 0  
        self.total_audio_chunks: int = 0 

        self.is_first_chunk = True
        self.server_url: str = os.getenv("SERVER_URL_WS", "ws://localhost:8000//ws/voice_chat_stream_socket")  
        console_logger.info(f"Server url: {self.server_url}")

        self.ws = None
    
    console_tracer.start_as_current_span("AgentProxySockets - add_audio")
    async def add_audio(self, frames):
        if not self.ws:
            self.ws = await websockets.connect(self.server_url)   
            console_logger.info(f"Connected to server: {self.server_url}")
            await self.ws.send("start")
            await self.ws.send(f"device_id:{self.device_id}")

        self.total_audio_chunks_sent += 1
        
        for frame in frames:
            console_logger.debug(f'Sending audio chunk of size: {len(frame) / 1024:.2f} KB')  
            self.total_audio_size_sent += len(frame)
            await self.ws.send(frame)
    
    console_tracer.start_as_current_span("AgentProxySockets - stop")
    async def add_audio_complete(self):
        console_logger.info("Sending stop command to server. this marks end of audio recording")
        await self.ws.send("stop")

    @console_tracer.start_as_current_span("AgentProxySockets - generate_audio_response")
    async def generate_audio_response(self):
        console_logger.info("Send data complete now, wating for audio response from server")
        server_response = console_tracer.start_span("server_response_time")
        ap: AudioPlayer = AudioPlayer(parent_context=context_api.get_current())  
        play_filler_music(ap, 1)         
        try:
            while True:
                audio_chunk = await self.ws.recv()
                if isinstance(audio_chunk, bytes):
                    if self.is_first_chunk:
                        self.is_first_chunk = False
                        server_response.end()
                        console_logger.info(f"Received First audio chunk of size: {len(audio_chunk)/ 1024:.2f} KB") 

                    self.total_audio_size += len(audio_chunk)
                    self.total_audio_chunks += 1
                    ap.add_audio([audio_chunk])
                else:
                    console_logger.info(f"Received non-bytes message from server: {audio_chunk}")

            
        except websockets.exceptions.ConnectionClosedOK:
            # The server is expected to close the connection once done
            pass
        except Exception as e:  
            traceback.print_exc() 
            console_logger.error(f"Error generating audio chunks: {e}")
        finally:
            if self.ws:
                await self.ws.close()
           
        console_logger.info("Client: Disconnected from server.")
        console_logger.info(f'Total audio size sent in KB: {self.total_audio_size_sent / 1024:.2f} KB')  
        console_logger.info(f"Total audio chunks sent: {self.total_audio_chunks}")

        console_logger.info(f'Total audio size received in KB: {self.total_audio_size / 1024:.2f} KB')  
        console_logger.info(f"Total audio chunks received: {self.total_audio_chunks}")
        ap.add_audio_complete()  
        ap.wait_for_completion()  
        console_logger.info(f"Finished generate_audio_response")
        
@console_tracer.start_as_current_span("get_agent_sroxy_sockets")
def get_agent_sroxy_sockets(device_id: str = None) -> AgentProxySocketsSingleApp | AgentProxySockets:
    if is_single_app:
        console_logger.info("Using AgentProxySocketsSingleApp")
        return AgentProxySocketsSingleApp(device_id=device_id)
    else:
        console_logger.info("Using AgentProxySockets")
        return AgentProxySockets(device_id=device_id)