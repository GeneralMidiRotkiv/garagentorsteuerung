# 'check_call' von 'subprocess' erlaubt es, shell-Befehle auszuführen
from subprocess import check_call
import time
import logging
from gpiozero import LED, Button, OutputDevice, exc
import configparser
import bot
import os

#! shutdown_btn = Button(16, hold_time=3)
#! closed_switch = Button(2)
#! opened_switch = Button(21)

relay_pin = 12

# ===================Mock-Buttons======================================
class Button:
    def __init__(self, is_pressed):
        self.is_pressed = None


shutdown_btn = Button(False)
closed_switch = Button(True)
opened_switch = Button(False)
# ======================================================================

# configure and define the logger
logging.basicConfig(filename="./doc/log.txt", level=logging.DEBUG)
logger = logging.getLogger()

# get the path to the current file
current_filepath = os.path.dirname(__file__)


class Command:
    """Represents a command received from Telegram"""

    keyword = None
    executed = False


class Door:
    """Represents the door and its attributes"""

    state = None
    opening_time = None
    recently_open = False


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
        time.strptime(deadline, "%H:%M")
    except ValueError as e:
        # if the deadline cannot be converted to a time tuple:
        logger.error(
            f"Error while converting the given 'deadline' value to a time tuple: {e}"
        )
    try:
        float(config_data["DEFAULT"]["max_open_time"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'max_open_time' value to a float: {e}"
        )
    try:
        int(config_data["DEFAULT"]["loop_sleep_time"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'loop_sleep_time' value to an integer: {e}"
        )
    try:
        int(config_data["CHAT_ID"]["chat_id_group"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'chat_id_group' value to an integer: {e}"
        )
    try:
        int(config_data["DEFAULT"]["relay_on_time"])
    except ValueError as e:
        logger.error(
            f"Error while converting the given 'relay_on_time' value to an integer: {e}"
        )
    return config_data


def check_door_position():
    """Check the position of the door by querying the tactile switches and returns the position.

    position values can be: 'closed', 'open' or 'in_transition'
    """
    # query the switch that indicates a closed door
    if closed_switch.is_pressed:
        return "closed"
    if opened_switch.is_pressed:
        return "open"
    if not closed_switch.is_pressed and opened_switch.is_pressed:
        return "in_transition"

def activate_relay(activation_duration):
    """Activates the relay connected to the door motor"""
    # build the representation of the relay
    relay = OutputDevice(relay_pin)
    # activate the relay for the defined time
    relay.on()
    time.sleep(activation_duration)
    relay.off()

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
    # create a 'Door' instance
    door = Door()
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
            logger.info(f"Received a new command: '{new_command.keyword}'")
        # check and store the door's position
        door.state = check_door_position()
        if door.state = "closed":
            pass
        else:
            #if the door is not 'closed':
            #check if an active command to close the door has already been issued
            if new_command.executed and new_command.keyword == 'close':
                activate_relay(settings["DEFAULT"]["relay_on_time"])
        # wait until the defined loop time has passed
        while time.time() - loop_starting_time < settings.getint(
            "DEFAULT", "loop_sleep_time"
        ):
            pass


main()