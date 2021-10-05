# 'check_call' von 'subprocess' erlaubt es, shell-Befehle auszuführen
from _typeshed import NoneType
from subprocess import check_call
import threading
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


class Alarm:
    """Represents an alarm"""

    name = None
    last_sent_time = None
    active = False


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


# load 'global' settings
global_settings = load_config()


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


def activate_relay(activation_duration, door_transiton_time):
    """Activates the relay connected to the door motor"""
    # build the representation of the relay
    relay = OutputDevice(relay_pin)
    # activate the relay for the defined time
    relay.on()
    logger.info("Activated the relay")
    time.sleep(activation_duration)
    relay.off()
    # wait the time it takes the door to close/open
    time.sleep(door_transiton_time)


def reposition_door(door, position, loop_settings):
    """Tries to reposition the door into the position defined by 'position'

    'door' needs to be an instance of 'Door'
    'position' can be 'open' or 'closed'
    """
    # activate the relay
    activate_relay(
        activation_duration=loop_settings["DEFAULT"]["relay_activation_duration"],
        door_transiton_time=loop_settings["DEFAULT"]["door_transition_time"],
    )
    # check the new door position
    door.state = check_door_position()
    # if the door is in the correct position now, go on
    if door.state == position:
        send_success_message(position)
    # if the door is not in the correct position now, try again
    else:
        activate_relay(
            activation_duration=loop_settings["DEFAULT"]["relay_activation_duration"],
            door_transiton_time=loop_settings["DEFAULT"]["door_transition_time"],
        )
        # check the position again
        door.state = check_door_position()
        if door.state == position:
            send_success_message(position)
        # if the door is not in the correct position after the second try, something is wrong and the door needs to be checked
        else:
            logger.info(
                "The door couldn't be positioned correctly on the second try and needs to be checked."
            )
            bot.send_message(
                bot_token=loop_settings["TOKEN"]["bot_token"],
                chat_id=loop_settings["CHAT_ID"]["chat_id_group"],
                message="Das Tor konnte wiederholt nicht in die richtige Position gefahren werden und sollte manuell überprüft werden.",
            )


def after_deadline(deadline):
    """Check whether it's after the deadline and return 'True' if that is the case."""
    # get and store the time of this loop iteration
    current_time = time.localtime()
    # calculate the elapsed seconds of the current day
    seconds_gone_today = current_time.tm_hour * 60 * 60 + current_time.tm_min * 60
    # calculate the seconds from midnight to deadline
    deadline_in_seconds = deadline.tm_hour * 60 * 60 + deadline.tm_min * 60
    # check if the time passed today is bigger than the deadline in seconds
    if seconds_gone_today >= deadline_in_seconds:
        logger.info("The system detected an open garage door after deadline.")
        return True
    return False


def handle_alarm(alarm):
    """Handles alarms and decides when to send one out"""
    # TODO: eine Nachricht senden, die 'offen lassen' oder 'jetzt schließen' als Option hat und diese Befehle dann ausführt
    while alarm.active:
        # create a thread that sends reminder messages in the background
        thread = threading.Thread(target=send_timed_alarm, args=[alarm], daemon=True)
    # if the alarm has been deactivated, stop the background thread
    thread.join()


def send_timed_alarm(alarm):
    """Sends a message depending on whether it is the first alarm or if a certain time has passed."""
    # get the time after which a new remind-message is neccessary
    reminder_time = global_settings["MESSAGE"]["reminder_delay"]
    # if 'last_sent_time' is 'None', no message has yet been sent
    if alarm.last_sent_time == NoneType:
        # send a message and set the message time
        bot.send_message(
            global_settings["TOKEN"]["bot_token"],
            global_settings["CHAT_ID"]["chat_id_group"],
            "Das Garagentor steht offen",
        )
        alarm.last_sent_time = time.time()
    else:
        # if there was a message sent already, check if a reminder is necessary
        if time.time() >= alarm.last_sent_time + reminder_time * 60:
            bot.send_message(
                global_settings["TOKEN"]["bot_token"],
                global_settings["CHAT_ID"]["chat_id_group"],
                "Das Garagentor steht offen",
            )


def send_success_message(position_keyword):
    """Sends a message containing the 'position_keyword'."""
    bot.send_message(
        global_settings["TOKEN"]["bot_token"],
        chat_id=global_settings["CHAT_ID"]["chat_id_group"],
        message=f"Die Tür wurde erfolgreich in Position '{position_keyword}' gefahren.",
    )


def main():
    # load the settings once to get the group id
    main_settings = load_config()
    # send a message to indicate the start of the program
    bot.send_message(
        bot_token=main_settings["TOKEN"]["bot_token"],
        chat_id=main_settings["CHAT_ID"]["chat_id_group"],
        message="Die Garagentorüberwachung hat begonnen 8-)",
    )
    # create a 'Command' instance that stores the most recent command permanently
    new_command = Command()
    # create a 'Door' instance
    door = Door()
    # create a 'Alarm' instance
    alarm = Alarm()
    while True:
        # get the starting-time of this loop iteration
        loop_starting_time = time.time()
        # load the settings from the config file
        loop_settings = load_config()
        # get the most recent update from the Telegram server
        current_update = bot.get_updates(loop_settings["TOKEN"]["bot_token"])
        # check if there is a command inside the current update
        if current_update:
            # if there is a command in the update, create a new Command instance
            # TODO: hier könnte die Überprüfung auf authorisierten user geschehen
            new_command.keyword = current_update[-1]["message"]["text"]
            logger.info(f"Received a new command: '{new_command.keyword}'")
        # check and store the door's position
        door.state = check_door_position()
        if door.state == "closed":
            # if the door is closed, nothing needs to be done
            pass
        else:
            # if the door is not 'closed':
            # check if an active command to close the door has already been issued
            if not new_command.executed and new_command.keyword == "close":
                reposition_door(door, "closed", loop_settings)
            # if no command has been issued, check if the deadline has been crossed
            elif after_deadline(deadline=loop_settings["DEFAULT"]["deadline"]):
                # if the alert is not yet active, activate it, then handle it accordingly
                if not alarm.active:
                    alarm.active = True
                    handle_alarm(alarm)
        # wait until the defined loop time has passed
        while time.time() - loop_starting_time < loop_settings.getint(
            "DEFAULT", "loop_sleep_time"
        ):
            pass


main()