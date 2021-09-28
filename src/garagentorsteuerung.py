# 'check_call' von 'subprocess' erlaubt es, shell-Befehle auszuführen
from subprocess import check_call
import time
import logging
from gpiozero import LED, Button
import configparser
from bot import send_message, send_custom_keyboard_message, get_updates

#! shutdown_btn = Button(16, hold_time=3)
#! closed_switch = Button(2)
#! opened_switch = Button(21)

shutdown_btn = False
closed_switch = True
opened_switch = False

# configure and define the logger
logging.basicConfig(filename="./doc/log.txt", level=logging.DEBUG)
logger = logging.getLogger()