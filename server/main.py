#uvicorn server.main:app --port=8000 --reload
import os
import json
import base64
from typing import  Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from server import agent_base
from server import utils_speech
import pydub
import io
import uuid
load_dotenv() 

from opentelemetry import context as context_api
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

class QueryInput(BaseModel):
    device_id: str
    user_input: Optional[str] = Field(default=None),  
    user_audio_input: Optional[str] = Field(default="text")  

@console_tracer.start_as_current_span("convert_amr_to_wav")
def convert_amr_to_wav(amr_input_base64_utf8 :str) -> str:
    console_logger.debug(f"Converting amr to wav received bytes : {len(amr_input_base64_utf8)}")
    buffer_input = io.BytesIO(base64.b64decode(amr_input_base64_utf8))
    buffer_input.name = "temp.amr"
    buffer_output = io.BytesIO()
    buffer_output.name = "temp.wav"
    audio = pydub.AudioSegment.from_file(buffer_input)   
    audio.export(buffer_output, format= "wav")
    buffer_output.seek(0)
    encoded_output = base64.b64encode(buffer_output.getvalue()).decode('utf-8')
    buffer_output.close()
    buffer_input.close()
    return encoded_output

@console_tracer.start_as_current_span("convert_wav_to_text")
def convert_wav_to_text(wav_base64_utf8 :str) -> str:
    query_text = utils_speech.speech_to_text_from_base64(wav_base64_utf8)
    return query_text

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

async def get_audio_stream_base64(query_input: QueryInput, type:str = "wav") -> str:
    # Create a span for tracing this function
    with console_tracer.start_as_current_span("get_audio_stream_base64") as span:
        # Add relevant attributes to the span
        span.set_attribute("audio.type", type)
        span.set_attribute("device_id", query_input.device_id)
        span.set_attribute("has_text_input", query_input.user_input is not None)
        span.set_attribute("audio_input_size", len(query_input.user_audio_input) if query_input.user_audio_input else 0)
        
        request_id = str(uuid.uuid4())
        span.set_attribute("request_id", request_id)
        
        console_logger.info(f"User input format: {type} and size: {len(query_input.user_audio_input)}, request_id: {request_id}")
        
        try:
            query_text = ""
            user_audio_input = query_input.user_audio_input
            if(query_input.user_input and query_input.user_input.strip()):
                query_text = query_input.user_input
            elif query_input.user_audio_input and len(query_input.user_audio_input) > 0:
                if type == "amr":
                    span.add_event("Converting AMR to WAV")
                    user_audio_input = convert_amr_to_wav(query_input.user_audio_input)
                    span.set_attribute("conversion_performed", True)

                query_text = convert_wav_to_text(user_audio_input) 

            span.add_event("Starting streaming response")
            chunk_count = 0
            async for audio_chunk in agent_base.get_conversation_response_streaming(
                device_id=query_input.device_id,
                user_input=query_text,
                user_audio_input=user_audio_input
            ):
                chunk_count += 1
                object_audio = json.dumps({"type":"audio", "audio": base64.b64encode(audio_chunk).decode('utf-8')})
                yield object_audio
                
            span.set_attribute("total_chunks", chunk_count)
            span.add_event("Completed streaming response")
            
        except Exception as e:
            error_msg = str(e)
            console_logger.error(f"Error in audio streaming: {error_msg}, request_id: {request_id}")
            span.record_exception(e)
            span.set_status("ERROR", error_msg)
            raise

async def get_audio_stream(device_id: str, streaming_stt : utils_speech.StreamingSTT) -> str:
    # Create a span for tracing this function
    with console_tracer.start_as_current_span("get_audio_stream") as span:
        # Add relevant attributes to the span
               
        request_id = str(uuid.uuid4())
        span.set_attribute("request_id", request_id)
        
        try:
            with console_tracer.start_as_current_span("tts") as span_tts:
                streaming_stt.wait_for_completion()  # wait for the audio to be added
                query_text = streaming_stt.get_text()

            span.add_event("Starting streaming response")
            chunk_count = 0
            async for audio_chunk in agent_base.get_conversation_response_streaming(
                device_id=device_id,
                user_input=query_text,
                user_audio_input=None
            ):
                chunk_count += 1
                yield audio_chunk
                
            span.set_attribute("total_chunks", chunk_count)
            span.add_event("Completed streaming response")
            
        except Exception as e:
            error_msg = str(e)
            console_logger.error(f"Error in audio streaming: {error_msg}, request_id: {request_id}")
            span.record_exception(e)
            span.set_status("ERROR", error_msg)
            raise

@app.get("/voice_chat_stream_amr")
async def chat_stream_amr(query_input: QueryInput):
    console_logger.info(f"Received User input: {query_input.user_input}")
    return StreamingResponse(get_audio_stream_base64(query_input = query_input, type= "amr"), status_code=200 , media_type='audio/wav')

@app.get("/voice_chat_stream_wav")
async def chat_stream_wav(query_input: QueryInput):
    console_logger.info(f"Received User input: {query_input.user_input}")
    return StreamingResponse(get_audio_stream_base64(query_input = query_input, type="wav"), status_code=200 , media_type='audio/wav')

@console_tracer.start_as_current_span("voice_chat_stream_socket")
@app.websocket("/ws/voice_chat_stream_socket")
async def chat_stream_socket(websocket: WebSocket):
    """
    WebSocket endpoint to receive audio chunks from the client,
    save them to a file, and then send the file back.
    """
    await websocket.accept()
    console_logger.info("Client connected.")
    streaming_stt = utils_speech.StreamingSTT(parent_context=context_api.get_current())
    streaming_stt.create_stream()

    device_id = None

    try:  
    # Wait for a "start" text message from client  
        audio_complete = False
        while not audio_complete:  
            msg = await websocket.receive_text()  
            if msg == "start":  
                # Begin accumulating audio data  
                console_logger.info("Server: Recording started.")  

                # In recording mode, read bytes until we get a "stop" message                  
                while not audio_complete: 
                    sub_msg = await websocket.receive()  
                    
                    # If client disconnects mid-recording  
                    if sub_msg["type"] == "websocket.disconnect":  
                        console_logger.info("Client disconnected.")  
                        return  

                    # If we receive binary audio data  
                    if sub_msg.get("bytes"):  
                        console_logger.debug(f"Received audio chunk of size: {len(sub_msg['bytes'])} bytes")
                        streaming_stt.add_audio([sub_msg["bytes"]])
                    # If we receive a text message (potentially "stop")  
                    elif sub_msg.get("text"):  
                        text_data = sub_msg["text"]  
                        if text_data.startswith("device_id:") and ":" in text_data:
                            device_id = text_data.split(":")[1].strip()
                            console_logger.info(f"Received device_id: {device_id}")
                        elif text_data == "stop":  
                            console_logger.info("Server: Recording stopped..")  
                            streaming_stt.add_audio_complete()
                            audio_complete = True
                        else:
                            console_logger.info(f"Server: Received unexpected message: {text_data}")
                    else:
                        console_logger.info("Server: Received unexpected message type.")
            else :  
                console_logger.info(f"Server: Received unexpected message: {msg}")  

        if device_id is not None:
            console_logger.info(f"Received device_id: {device_id}")
            async for audio_chunk in get_audio_stream(device_id=device_id, streaming_stt=streaming_stt):
                await websocket.send_bytes(audio_chunk) 
        
    except WebSocketDisconnect:  
        console_logger.info("Client disconnected unexpectedly.")  


    # Close connection after one full start/stop cycle  
    await websocket.close()  
    console_logger.info("Client connection closed.") 
    return