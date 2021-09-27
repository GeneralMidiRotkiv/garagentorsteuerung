import requests
import logging
import json
import time
import pyjokes
import configparser

# pprint erlaubt pretty printing
from pprint import pprint
from requests.api import request

# configure and define the logger
logging.basicConfig(filename="./doc/log.txt", level=logging.DEBUG)
logger = logging.getLogger()

# load the config data
config_data = configparser.ConfigParser()
config_data.read("./doc/config.txt")
token = config_data["TOKEN"]["bot_token"]
try:
    chat_id_vik = int(config_data["CHAT_ID"]["chat_id_vik"])
    chat_id_testbotgruppe = int(config_data["CHAT_ID"]["chat_id_group"])
except ValueError as e:
    logger.error(
        "An error occured while trying to convert one of the chat IDs to an integer"
    )
    raise e
# all queries to the Telegram Bot API must be served over HTTPS and need to be presented in this form: https://api.telegram.org/bot<token>/METHOD_NAME
query_url = f"https://api.telegram.org/bot{token}"


def print_request_error(function_name, response):
    """Prints the error that occured after sending a request"""
    print(
        f"Something went wrong while calling '{function_name}': \n {response['description']}"
    )


def send_message(chat_id, message):
    payload = {"chat_id": chat_id, "text": message}
    r = requests.post(f"{query_url}/sendMessage", params=payload)
    # print(r.url)
    r = r.json()
    # in case of a bad request:
    if not r["ok"]:
        print_request_error("send_message", r)
        return False


def send_custom_keyboard_message(chat_id, message, reply_markup):
    payload = {"chat_id": chat_id, "text": message, "reply_markup": reply_markup}
    r = requests.post(f"{query_url}/sendMessage", params=payload)
    # print(r.url)
    r = r.json()
    # in case of a bad request:
    if not r["ok"]:
        print_request_error("send_message", r)
        return False


def get_updates():
    """Returns the most recent updates of the bot or false if there are no new updates."""
    # load infos about the last update
    with open("./doc/updinf.json", "r") as upd_file:
        update_info = json.load(upd_file)
    # get the time of the last update
    last_update_time = update_info["time_of_last_upd"]
    # calculate the difference in seconds between now and the last update's time
    time_diff = time.time() - last_update_time
    # get the id of the last update, depending on the time since the last update:
    # if the time difference is less than 7 days:
    if time_diff < 7 * 24 * 3600:
        update_offset = update_info["last_upd_id"]
    # if the time difference is bigger than one week, the update_id will be set to a random number by telegram, so the old one is irrelevant
    else:
        update_offset = 0
    # set the payload for the request to get an update
    payload = {"offset": update_offset + 1, "allowed_updates": ["message"]}
    r = requests.get(f"{query_url}/getUpdates", params=payload)
    # change the response to a .json-encoded version
    r = r.json()
    # in case of a bad request:
    if not r["ok"]:
        print_request_error("get_updates", r)
        return False
    # after checking the 'ok' status, only the 'result' is of interest to us
    result = r["result"]
    # get the most recent update_id
    try:
        # try to get the last update's update_id and time
        last_update_id = result[-1]["update_id"]
        last_update_time = result[-1]["message"]["date"]
        logger.info(f"Got the most recent update: {result}")
    except IndexError:
        # if there are no new updates:
        logger.info(f"No new updates")
        return False
    # update the update time and id in the update_info dict
    update_info["time_of_last_upd"] = last_update_time
    update_info["last_upd_id"] = last_update_id
    # write the new 'update_info' to the updinf file
    with open("./doc/updinf.json", "w") as upd_file:
        json.dump(update_info, upd_file)
    return result


def send_joke(chat_id):
    """Sends a joke retrieved from pyjokes"""
    send_message(chat_id, pyjokes.get_joke(language="de", category="all"))


def toggle_led(chat_id):
    """Toggle the led state and sends an according message"""
    pass


command_map = {
    "/joke": send_joke,
    "/led": toggle_led,
}

# Example for a custom keyboard that closes after the user has chosen an option
custom_keyboard = json.dumps(
    {
        "keyboard": [["Row11", "Row12"], ["Row21"]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
)


def chat_loop(chat_id):
    send_message(chat_id, "Up and running ;)")
    send_custom_keyboard_message(chat_id, "Auswahl:", custom_keyboard)
    # while True:
    #     last_update = get_updates()
    #     if last_update:
    #         message_text = last_update[-1]["message"]["text"]
    #         if message_text in command_map:
    #             command_map[message_text](chat_id)
    #     time.sleep(1)


chat_loop(chat_id_testbotgruppe)
# send_message(chat_id_testbotgruppe, "Aha")
