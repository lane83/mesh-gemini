#!/usr/bin/env python3
import meshtastic
from meshtastic.tcp_interface import TCPInterface
from pubsub import pub
import google.generativeai as genai
import time
import sys
import signal
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_KEY = "YOURGEMINIAPIKEY"
TARGET_CHANNEL = YOURCHANNELNUMBER
HOST = "MESHTASTICDEVICEIPADDRESS"
PORT = 4403

interface = None

def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    if interface:
        interface.close()
    sys.exit(0)

def get_llm_response(message):
    try:
        response = model.generate_content(
            f"Respond to this message in under 200 characters: {message}",
            generation_config={
                'temperature': 0.7,
                'max_output_tokens': 100
            }
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)[:190]}"

def on_meshtastic_message(packet, interface=None):
    try:
        if 'decoded' not in packet or 'text' not in packet['decoded']:
            return
            
        message = packet['decoded']['text']
        logger.info(f"Message received: {message}")
        
        response = get_llm_response(message)
        truncated_response = response[:200]
        
        if interface:
            interface.sendText(
                truncated_response,
                channelIndex=TARGET_CHANNEL,
                wantResponse=True,
                onResponse=lambda p: logger.info(f"Message delivered: {p}")
            )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def main():
    global interface
    
    if not API_KEY:
        logger.error("API_KEY not set")
        sys.exit(1)

    genai.configure(api_key=API_KEY)
    global model
    model = genai.GenerativeModel('gemini-pro')
    
    try:
        interface = TCPInterface(HOST)
        pub.subscribe(on_meshtastic_message, "meshtastic.receive.text")
        
        logger.info(f"Connected to radio at {HOST}:{PORT}")
        logger.info(f"Bridge running on channel {TARGET_CHANNEL}")
        
        while True:
            time.sleep(0.1)
            
    except ConnectionRefusedError:
        logger.error(f"Connection refused to {HOST}:{PORT}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        if interface:
            interface.close()
        sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
