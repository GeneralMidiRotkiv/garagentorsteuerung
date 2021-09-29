# 'check_call' von 'subprocess' erlaubt es, shell-Befehle auszuführen
from subprocess import check_call
import time
import logging
from gpiozero import LED, Button
import configparser
import bot
import os

#! shutdown_btn = Button(16, hold_time=3)
#! closed_switch = Button(2)
#! opened_switch = Button(21)

shutdown_btn = False
closed_switch = True
opened_switch = False

# configure and define the logger
logging.basicConfig(filename="./doc/log.txt", level=logging.DEBUG)
logger = logging.getLogger()

# get the path to the current file
current_filepath = os.path.dirname(__file__)


class Command:
    keyword = None
    executed = False


def load_config():
    """Loads the settings, validates them and returns the configparser instance containing the settings"""
    # start a config parser object
    config_data = configparser.ConfigParser()
    # load the data inside the config file
    config_data.read(os.path.join(current_filepath, "doc", "config.txt"))
    # get the deadline
    deadline = config_data["DEFAULT"]["deadline"]
    try:
        # try to convert the deadline to a time tuple
        deadline = time.strptime(deadline, "%H:%M")
    except ValueError as e:
        # if the deadline cannot be converted to a time tuple:
        logger.error(
            f"Error while converting the given 'deadline' value to a time tuple: {e}"
        )
    try:
        max_open_time = float(config_data["DEFAULT"]["max_open_time"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'max_open_time' value to a float: {e}"
        )
    try:
        loop_sleep_time = int(config_data["DEFAULT"]["loop_sleep_time"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'loop_sleep_time' value to an integer: {e}"
        )
    try:
        chat_id_group = int(config_data["CHAT_ID"]["chat_id_group"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'chat_id_group' value to an integer: {e}"
        )
    return config_data


def main():
    # load the settings once to get the group id
    settings = load_config()
    # send a message to indicate the start of the program
    bot.send_message(
        bot_token=settings["TOKEN"]["bot_token"],
        chat_id=settings["CHAT_ID"]["chat_id_group"],
        message="Die Garagentorüberwachung hat begonnen 8-)",
    )
    # create a 'Command' instance that stores the most recent command permanently
    new_command = Command()
    while True:
        # get the starting-time of this loop iteration
        loop_starting_time = time.time()
        # load the settings from the config file
        settings = load_config()
        # get the most recent update from the Telegram server
        current_update = bot.get_updates(settings["TOKEN"]["bot_token"])
        # check if there is a command inside the current update
        if current_update:
            # if there is a command in the update, create a new Command instance
            # TODO: hier könnte die Überprüfung auf authorisierten user geschehen
            new_command.keyword = current_update[-1]["message"]["text"]
        # wait until the defined loop time has passed
        while time.time() - loop_starting_time < settings.getint(
            "DEFAULT", "loop_sleep_time"
        ):
            pass


main()