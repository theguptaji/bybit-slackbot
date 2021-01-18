import os
import logging
import asyncio
import ssl as ssl_lib

import certifi
from slack_sdk.web import WebClient
from slack_sdk.rtm import RTMClient

from crypto_alert import CryptoAlert

"""This file serves as an example for how to create the same app, but running asynchronously."""

# For simplicity we'll store our app data in-memory with the following data structure.
# cryptoalert_sent = {"channel": {"user_id": cryptoTutorial}}
cryptoalert_sent = {}


async def start_crypto(web_client: WebClient, user_id: str, channel: str):
    # Create a new crypto tutorial.
    crypto_alert = CryptoAlert(channel)

    # Get the crypto message payload
    message = crypto_alert.get_message_payload()

    # Post the crypto message in Slack
    response = await web_client.chat_postMessage(**message)

    # Capture the timestamp of the message we've just posted so
    # we can use it to update the message after a user
    # has completed an crypto task.
    crypto_alert.timestamp = response["ts"]

    # Store the message sent in cryptoalert_sent
    if channel not in cryptoalert_sent:
        cryptoalert_sent[channel] = {}
    cryptoalert_sent[channel][user_id] = crypto_alert


# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
# Here we'll link the crypto_message callback to the 'team_join' event.
@RTMClient.run_on(event="team_join")
async def crypto_message(**payload):
    """Create and send an crypto welcome message to new users. Save the
    time stamp of this message so we can update this message in the future.
    """
    # Get WebClient so you can communicate back to Slack.
    web_client = payload["web_client"]

    # Get the id of the Slack user associated with the incoming event
    user_id = payload["data"]["user"]["id"]

    # Open a DM with the new user.
    response = web_client.conversations_open(users=user_id)
    channel = response["channel"]["id"]

    # Post the crypto message.
    await start_crypto(web_client, user_id, channel)


# ============= Reaction Added Events ============= #
# When a users adds an emoji reaction to the crypto message,
# the type of the event will be 'reaction_added'.
# Here we'll link the update_emoji callback to the 'reaction_added' event.
@RTMClient.run_on(event="reaction_added")
async def update_emoji(**payload):
    """Update the crypto welcome message after receiving a "reaction_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data["item"]["channel"]
    user_id = data["user"]

    # Get the original tutorial sent.
    crypto_alert = cryptoalert_sent[channel_id][user_id]

    # Mark the reaction task as completed.
    crypto_alert.reaction_task_completed = True

    # Get the new message payload
    message = crypto_alert.get_message_payload()

    # Post the updated message in Slack
    updated_message = await web_client.chat_update(**message)

    # Update the timestamp saved on the crypto tutorial object
    crypto_alert.timestamp = updated_message["ts"]


# =============== Pin Added Events ================ #
# When a users pins a message the type of the event will be 'pin_added'.
# Here we'll link the update_pin callback to the 'reaction_added' event.
@RTMClient.run_on(event="pin_added")
async def update_pin(**payload):
    """Update the crypto welcome message after receiving a "pin_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data["channel_id"]
    user_id = data["user"]

    # Get the original tutorial sent.
    crypto_alert = cryptoalert_sent[channel_id][user_id]

    # Mark the pin task as completed.
    crypto_alert.pin_task_completed = True

    # Get the new message payload
    message = crypto_alert.get_message_payload()

    # Post the updated message in Slack
    updated_message = await web_client.chat_update(**message)

    # Update the timestamp saved on the crypto tutorial object
    crypto_alert.timestamp = updated_message["ts"]


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@RTMClient.run_on(event="message")
async def message(**payload):
    """Display the crypto welcome message after receiving a message
    that contains "start".
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data.get("channel")
    user_id = data.get("user")
    text = data.get("text")

    if text and text.lower() == "start":
        return await start_crypto(web_client, user_id, channel_id)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    rtm_client = RTMClient(
        token=slack_token, ssl=ssl_context, run_async=True, loop=loop
    )
    loop.run_until_complete(rtm_client.start())