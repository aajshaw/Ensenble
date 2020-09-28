from pygame import mixer
import socket
from sys import byteorder
from Config import Config
import os
import sys

def ring_bells(addr, port):
    app_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    
    config = Config()
    
    COMMAND_START = config.getint('STRIKE_COMMANDS', 'command_start')
    EXIT = config.getint('STRIKE_COMMANDS', 'exit')
    LOOK_TO = config.getint('STRIKE_COMMANDS', 'look_to')
    GO = config.getint('STRIKE_COMMANDS', 'go')
    BOB = config.getint('STRIKE_COMMANDS', 'bob')
    SINGLE = config.getint('STRIKE_COMMANDS', 'single')
    THATS_ALL = config.getint('STRIKE_COMMANDS', 'thats_all')
    STAND = config.getint('STRIKE_COMMANDS', 'stand_next')
    
    mixer.init(frequency = 8000, channels = 1, buffer = 256)
    mixer.set_num_channels(8);

    bells = {} # A dict so that bells can be accessed by bell number starting with one

    for ndx in range(1, config.getint('BELLS', 'bells') + 1):
        bells[ndx] = mixer.Sound(app_path + '/data/bell_' + str(ndx) + '.wav')
    
    look_to = mixer.Sound(app_path + '/data/LookTo.wav')
    go = mixer.Sound(app_path + '/data/Go.wav')
    bob = mixer.Sound(app_path + '/data/Bob.wav')
    single = mixer.Sound(app_path + '/data/Single.wav')
    thats_all = mixer.Sound(app_path + '/data/ThatsAll.wav')
    stand = mixer.Sound(app_path + '/data/Stand.wav')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((addr, port))

    while True:
        data, addr = sock.recvfrom(8)
        command = int.from_bytes(data, byteorder)
        if command == EXIT:
            break
        elif command >= COMMAND_START:
            if command == LOOK_TO:
                look_to.play()
            elif command == GO:
                go.play()
            elif command == BOB:
                bob.play()
            elif command == SINGLE:
                single.play()
            elif command == THATS_ALL:
                thats_all.play()
            elif command == STAND:
                stand.play()
        else:
            # Command is just a bell to be played
            bells[command].play()
