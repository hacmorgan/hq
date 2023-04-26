#!/usr/bin/env python3


"""
There are a few ways to control Google Home devices using Python, but the most popular method is to use the Google Assistant SDK. The Google Assistant SDK allows you to control Google Home devices by sending voice commands to the Google Assistant.

Here are the basic steps to control Google Home devices using Python:

    Set up the Google Assistant SDK on your development machine by following the instructions on the Google Assistant SDK website.

    Download the credentials.json file from the Google Cloud Console and place it in the same directory as your Python script.

    Install the Google Assistant library for Python by running pip install google-assistant-sdk[samples]

    Write a Python script that uses the Google Assistant library to send voice commands to the Google Assistant.

Here's an example of a Python script that uses the Google Assistant SDK to control a Google Home device:
"""


from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc,
)
import grpc
import os
import time

# Assistant credentials
ASSISTANT_CREDENTIALS = os.path.join(
    os.path.expanduser("~"), ".config", "google-oauthlib-tool", "credentials.json"
)

# Assistant language code
LANGUAGE_CODE = "en-US"

# Assistant device model ID
DEVICE_MODEL_ID = "<YOUR_DEVICE_MODEL_ID>"

# Assistant device instance ID
DEVICE_INSTANCE_ID = "<YOUR_DEVICE_INSTANCE_ID>"


def send_text_query(text_query):
    """Send a text query to the Assistant and return the response."""
    # Create a gRPC channel to the Assistant
    channel = grpc.secure_channel(
        "embeddedassistant.googleapis.com:443", grpc.ssl_channel_credentials()
    )
    stub = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)

    # Create a config for the Assistant
    config = embedded_assistant_pb2.AssistConfig(
        audio_out_config=embedded_assistant_pb2.AudioOutConfig(
            encoding="LINEAR16", sample_rate_hertz=16000, volume_percentage=0
        ),
        dialog_state_in=embedded_assistant_pb2.DialogStateIn(
            language_code=LANGUAGE_CODE,
            device_model_id=DEVICE_MODEL_ID,
            device_instance_id=DEVICE_INSTANCE_ID,
        ),
        device_config=embedded_assistant_pb2.DeviceConfig(
            device_id="default", device_model_id=DEVICE_MODEL_ID
        ),
        text_query=text_query,
    )

    # Send the text query to the Assistant
    response = stub.Assist(config, timeout=10)
    return response


if __name__ == "__main__":
    text_query = "turn on the lights"
    response = send_text_query(text_query)
    for resp in response:
        print(resp)
