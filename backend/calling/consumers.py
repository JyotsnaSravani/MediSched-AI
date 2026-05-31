"""
WebSocket Consumer for GPT-Realtime-2 Audio Streaming
Handles bidirectional audio streaming between Twilio and OpenAI Realtime API
"""

import json
import asyncio
import websockets
import base64
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from asgiref.sync import sync_to_async
from .conversational_ai_realtime import create_realtime_session_config

logger = logging.getLogger(__name__)


class RealtimeAIConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time AI voice conversations.
    
    Flow:
    1. Twilio connects via WebSocket
    2. We connect to OpenAI Realtime API
    3. Audio streams bidirectionally:
       - Twilio → OpenAI (patient speech)
       - OpenAI → Twilio (AI response)
    4. GPT-Realtime-Whisper transcribes in real-time
    5. GPT-Realtime-2 generates responses with GPT-5-class reasoning
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_ws = None
        self.patient = None
        self.call_log = None
        self.stream_sid = None
        self.call_sid = None
        self.transcription = []
        self.heartbeat_task = None
        self.is_active = True
    
    async def connect(self):
        """Accept WebSocket connection from Twilio."""
        try:
            await self.accept()
            logger.info(f"WebSocket connection accepted from {self.scope.get('client')}")
            
            # Get parameters from query string
            query_string = self.scope['query_string'].decode()
            logger.info(f"Query string: {query_string}")
            
            query_params = {}
            if query_string:
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value
            
            patient_id = query_params.get('patient_id')
            call_log_id = query_params.get('call_log_id')
            
            logger.info(f"Patient ID: {patient_id}, Call Log ID: {call_log_id}")
            
            # Load patient and call log
            self.patient = await self.get_patient(patient_id)
            self.call_log = await self.get_call_log(call_log_id)
            
            if not self.patient:
                logger.error(f"Patient not found: {patient_id}")
                await self.close()
                return
                
            if not self.call_log:
                logger.error(f"Call log not found: {call_log_id}")
                await self.close()
                return
            
            logger.info(f"WebSocket connected for patient {self.patient.full_name} (ID: {self.patient.id})")
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected: {close_code}")
        
        # Stop heartbeat
        self.is_active = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        # Close OpenAI connection
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception as e:
                logger.warning(f"Error closing OpenAI WebSocket: {e}")
                pass
        
        # Save transcription
        if self.transcription and self.call_log:
            await self.save_transcription()
    
    async def receive(self, text_data=None, bytes_data=None):
        """Receive messages from Twilio."""
        try:
            if text_data:
                data = json.loads(text_data)
                event_type = data.get('event')
                
                if event_type == 'start':
                    await self.handle_start(data)
                elif event_type == 'media':
                    await self.handle_media(data)
                elif event_type == 'stop':
                    await self.handle_stop(data)
                elif event_type == 'mark':
                    await self.handle_mark(data)
                    
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
    
    async def handle_start(self, data):
        """Handle stream start event from Twilio."""
        self.stream_sid = data['start']['streamSid']
        self.call_sid = data['start']['callSid']
        
        logger.info(f"Stream started: {self.stream_sid}")
        
        # Connect to OpenAI Realtime API
        await self.connect_to_openai()
    
    async def handle_media(self, data):
        """Handle incoming audio from Twilio."""
        if not self.openai_ws:
            return
        
        try:
            # Get audio payload (base64 encoded PCM16)
            audio_payload = data['media']['payload']
            
            # Forward to OpenAI Realtime API
            await self.openai_ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_payload
            }))
            
        except Exception as e:
            logger.error(f"Error handling media: {e}")
    
    async def handle_stop(self, data):
        """Handle stream stop event from Twilio."""
        logger.info(f"Stream stopped: {self.stream_sid}")
        await self.disconnect(1000)
    
    async def handle_mark(self, data):
        """Handle mark event from Twilio."""
        # Used for synchronization
        pass
    
    async def connect_to_openai(self):
        """Connect to OpenAI Realtime API."""
        try:
            # OpenAI Realtime API endpoint
            openai_url = f"wss://api.openai.com/v1/realtime?model=gpt-realtime-2"
            
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            # Connect to OpenAI with aggressive keepalive settings
            self.openai_ws = await websockets.connect(
                openai_url,
                extra_headers=headers,
                ping_interval=15,  # Send ping every 15 seconds (more frequent)
                ping_timeout=10,  # Wait 10 seconds for pong
                close_timeout=10,  # Wait 10 seconds for close handshake
                max_size=10 * 1024 * 1024,  # 10MB max message size
                compression=None  # Disable compression for lower latency
            )
            
            logger.info("Connected to OpenAI Realtime API with aggressive keepalive")
            
            # Send session configuration
            session_config = await sync_to_async(create_realtime_session_config)(
                self.patient,
                self.call_log.appointment,
                self.call_log.call_type
            )
            await self.openai_ws.send(json.dumps(session_config))
            logger.info("Session configuration sent to OpenAI")
            
            # Trigger initial greeting from AI
            await asyncio.sleep(0.5)  # Brief delay to ensure session is ready
            await self.openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "Start the call with your greeting now."
                }
            }))
            logger.info("Initial greeting triggered")
            
            # Enable turn detection after greeting
            await asyncio.sleep(2)  # Wait for greeting to start
            await self.openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.3,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800,
                        "create_response": True
                    }
                }
            }))
            logger.info("Turn detection enabled")
            
            # Start listening to OpenAI responses
            asyncio.create_task(self.listen_to_openai())
            
            # Start heartbeat to keep connection alive
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
            
            # Start Twilio keepalive
            asyncio.create_task(self.send_twilio_keepalive())
            
        except Exception as e:
            logger.error(f"Error connecting to OpenAI: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def send_twilio_keepalive(self):
        """Send periodic keepalive to Twilio to prevent disconnection."""
        try:
            while self.is_active and self.stream_sid:
                await asyncio.sleep(25)  # Send every 25 seconds
                if self.stream_sid:
                    try:
                        await self.send(text_data=json.dumps({
                            "event": "mark",
                            "streamSid": self.stream_sid,
                            "mark": {
                                "name": f"keepalive_{int(asyncio.get_event_loop().time())}"
                            }
                        }))
                        logger.debug("Keepalive sent to Twilio")
                    except Exception as e:
                        logger.warning(f"Twilio keepalive failed: {e}")
        except asyncio.CancelledError:
            logger.info("Twilio keepalive task cancelled")
        except Exception as e:
            logger.error(f"Twilio keepalive error: {e}")
    
    async def send_heartbeat(self):
        """Send periodic heartbeat to keep WebSocket alive."""
        try:
            while self.is_active and self.openai_ws:
                await asyncio.sleep(20)  # Send heartbeat every 20 seconds (more frequent)
                if self.openai_ws and not self.openai_ws.closed:
                    # Send a ping to keep connection alive
                    try:
                        await self.openai_ws.ping()
                        logger.debug("Heartbeat sent to OpenAI")
                        
                        # Also send a keep-alive message to Twilio
                        if self.stream_sid:
                            await self.send(text_data=json.dumps({
                                "event": "mark",
                                "streamSid": self.stream_sid,
                                "mark": {
                                    "name": "keepalive"
                                }
                            }))
                            logger.debug("Keepalive sent to Twilio")
                    except Exception as e:
                        logger.warning(f"Heartbeat failed: {e}")
                        # Don't break - try to recover
        except asyncio.CancelledError:
            logger.info("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    async def listen_to_openai(self):
        """Listen for responses from OpenAI Realtime API."""
        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                event_type = data.get('type')
                
                if event_type == 'response.audio.delta':
                    # Audio response from AI
                    await self.send_audio_to_twilio(data['delta'])
                    
                elif event_type == 'response.audio_transcript.delta':
                    # Transcription of AI response
                    transcript = data.get('delta', '')
                    self.transcription.append({
                        'speaker': 'AI',
                        'text': transcript
                    })
                    
                elif event_type == 'conversation.item.input_audio_transcription.completed':
                    # Transcription of patient speech (GPT-Realtime-Whisper)
                    transcript = data.get('transcript', '')
                    self.transcription.append({
                        'speaker': 'Patient',
                        'text': transcript
                    })
                    logger.info(f"Patient said: {transcript}")
                    
                elif event_type == 'response.function_call_arguments.done':
                    # Tool call from AI
                    await self.handle_tool_call(data)
                    
                elif event_type == 'response.done':
                    # Response completed - keep connection alive
                    logger.debug("Response completed, connection still active")
                    
                elif event_type == 'session.created':
                    # Session created successfully
                    logger.info("OpenAI session created successfully")
                    
                elif event_type == 'session.updated':
                    # Session updated successfully
                    logger.info("OpenAI session updated successfully")
                    
                elif event_type == 'error':
                    error_msg = data.get('error', {})
                    logger.error(f"OpenAI error: {error_msg}")
                    
                    # Check if it's a recoverable error
                    error_code = error_msg.get('code')
                    if error_code in ['rate_limit_exceeded', 'server_error']:
                        logger.info("Recoverable error, continuing...")
                        # Wait a bit and continue
                        await asyncio.sleep(1)
                    else:
                        logger.error("Non-recoverable error, but keeping connection open")
                        # Don't close - let the call continue
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"OpenAI WebSocket closed: {e.code} - {e.reason}")
            # Try to reconnect if connection was lost unexpectedly
            if self.is_active and e.code != 1000:  # 1000 = normal closure
                logger.info("Attempting to reconnect to OpenAI...")
                try:
                    await self.connect_to_openai()
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error}")
        except Exception as e:
            logger.error(f"Error listening to OpenAI: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't close - keep the call alive
    
    async def send_audio_to_twilio(self, audio_delta):
        """Send AI audio response to Twilio."""
        try:
            # Send audio to Twilio
            await self.send(text_data=json.dumps({
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_delta
                }
            }))
        except Exception as e:
            logger.error(f"Error sending audio to Twilio: {e}")
    
    async def handle_tool_call(self, data):
        """Handle tool/function calls from AI."""
        try:
            from .conversational_ai_realtime import RealtimeConversationalAI
            
            function_name = data.get('name')
            arguments = json.loads(data.get('arguments', '{}'))
            call_id = data.get('call_id')
            
            logger.info(f"Tool call: {function_name} with {arguments}")
            
            # Execute tool
            ai = RealtimeConversationalAI(
                self.patient,
                self.call_log.appointment,
                self.call_log.call_type
            )
            result = await sync_to_async(ai.execute_tool)(function_name, arguments)
            
            # Send result back to OpenAI
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }))
            
            # Request AI to respond
            await self.openai_ws.send(json.dumps({
                "type": "response.create"
            }))
            
        except Exception as e:
            logger.error(f"Error handling tool call: {e}")
    
    async def save_transcription(self):
        """Save conversation transcription to database."""
        try:
            from transcriptions.models import Transcription
            
            # Combine transcription
            full_text = "\n\n".join([
                f"{item['speaker']}: {item['text']}"
                for item in self.transcription
            ])
            
            # Save to database
            await sync_to_async(Transcription.objects.create)(
                call_log=self.call_log,
                appointment=self.call_log.appointment,
                text=full_text,
                status='COMPLETED',
                whisper_model='gpt-realtime-whisper',
                confidence_score=0.95
            )
            
            logger.info(f"Transcription saved for call {self.call_log.id}")
            
        except Exception as e:
            logger.error(f"Error saving transcription: {e}")
    
    @sync_to_async
    def get_patient(self, patient_id):
        """Get patient from database."""
        from patients.models import Patient
        try:
            return Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return None
    
    @sync_to_async
    def get_call_log(self, call_log_id):
        """Get call log from database."""
        from calling.models import CallLog
        try:
            return CallLog.objects.select_related('appointment').get(id=call_log_id)
        except CallLog.DoesNotExist:
            return None
