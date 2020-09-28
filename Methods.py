from threading import Thread
import socket
from time import sleep
from sys import byteorder
from Config import Config
import configparser
from Row import Row
import os
import sys

def bell_indicators(MAX_BELLS,
                    INDICATE_BELL_NUMBER_SHIFT,
                    INDICATE_BELL_HANDSTROKE,
                    INDICATE_BELL_BACKSTROKE,
                    INDICATE_BELL_GRAPHIC_SHOW,
                    INDICATE_BELL_GRAPHIC_CLEAR):
    hand = {}
    back = {}
    graphic_show = {}
    graphic_clear = {}
    for ndx in range(MAX_BELLS):
        hand[ndx] = INDICATE_BELL_HANDSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        back[ndx] = INDICATE_BELL_BACKSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        graphic_show[ndx] = INDICATE_BELL_GRAPHIC_SHOW | (ndx << INDICATE_BELL_NUMBER_SHIFT)
        graphic_clear[ndx] = INDICATE_BELL_GRAPHIC_CLEAR | (ndx << INDICATE_BELL_NUMBER_SHIFT)
    
    return hand, back, graphic_show, graphic_clear

class Method():
  def __init__(self, file, cover = False, load_rows = True, intro_courses = 1, method_courses = 1):
    definition = configparser.ConfigParser()
    definition.optionxform = str # Don't want keys to be lower cased
    
    definition.read(file)
    self.name = definition.get('INFO', 'name')
    self.bells = definition.getint('INFO', 'bells')
    self.frame_length = definition.getint('INFO', 'frame_length', fallback = self.bells * 2)
    self.cover = cover
    if cover:
      self.bells = self.bells + 1
    self.rows = definition.getint('INFO', 'rows')
    
    self.rows = []
    
    if load_rows:
        # Build the intro courses
        for ndx in range(intro_courses):
            for r in range(2): # Handstroke and backstroke in a course of rounds
                row = Row('I' + str(ndx * 2 + r + 1), self.frame_length)
                for b in range(self.bells):
                    row.add_bell(b + 1)
                self.rows.append(row)
                    
        # Add 'Go method' to the final round of the intro
        self.rows[len(self.rows) - 1].call_go = True
        
        # Load the method rows
        for ndx in range(method_courses):
            for r in definition.items('ROWS'):
              row = Row(r[0], self.frame_length)
              items = r[1].split()
              for i in items:
                if i == '(G)':
                  row.call_go = True
                elif i == '(A)':
                  row.call_thats_all = True
                elif i == '(B)':
                  row.call_bob = True
                elif i == '(S)':
                  row.call_single = True
                elif i == '(N)':
                  row.call_stand = True
                else:
                  bell = int(i)
                  row.add_bell(bell)
              
              if cover:
                row.add_bell(self.bells)
                
              self.rows.append(row)
        
        # Add 'Thats all' to the second to last row of the method
        self.rows[len(self.rows) - 2].call_thats_all = True
        
        # Build the extro courses
        for r in range(2): # Handstroke and backstroke in a course of rounds
          row = Row('E' + str(ndx * 2 + r + 1), self.frame_length)
          for b in range(self.bells):
            row.add_bell(b + 1)
          self.rows.append(row)
                    
        # Add 'Stand next' to the second to last row of the extro
        self.rows[len(self.rows) - 2].call_stand = True
    
def methods(conn, ring_addr, ring_port):
    app_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))

    config = Config()

    MAX_BELLS = config.getint('BELLS', 'bells')
    GO = config.getint('STRIKE_COMMANDS', 'go')
    THATS_ALL = config.getint('STRIKE_COMMANDS', 'thats_all')
    BOB = config.getint('STRIKE_COMMANDS', 'bob')
    SINGLE = config.getint('STRIKE_COMMANDS', 'single')
    STAND = config.getint('STRIKE_COMMANDS', 'stand_next')
    INDICATE_BELL_NUMBER_SHIFT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_bell_number_shift')
    INDICATE_BELL_HANDSTROKE = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_bell') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_BACKSTROKE = INDICATE_BELL_HANDSTROKE + \
                               (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_shift'))
    INDICATE_BELL_GRAPHIC_CLEAR = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_graphic') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_GRAPHIC_SHOW = INDICATE_BELL_GRAPHIC_CLEAR + \
                                 (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_shift'))
                                 
    handstroke_indicators, backstroke_indicators, graphic_show_indicators, graphic_clear_indicators = bell_indicators(MAX_BELLS,
                                                                                                                      INDICATE_BELL_NUMBER_SHIFT,
                                                                                                                      INDICATE_BELL_HANDSTROKE,
                                                                                                                      INDICATE_BELL_BACKSTROKE,
                                                                                                                      INDICATE_BELL_GRAPHIC_SHOW,
                                                                                                                      INDICATE_BELL_GRAPHIC_CLEAR)
    
    bells = [True] * MAX_BELLS
    stop_playing = False
    method = None
    pace = 3.0
    pause = pace / MAX_BELLS
    courses = 1
    intro_rounds = 1
    
    def play(ring_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ndx = 0
        position = 1
        stroke_type = "B"
        LOOK_TO = config.getint('STRIKE_COMMANDS', 'look_to')
        
        sleep(0.1) # To let ringer process startup
        
        sock.sendto(LOOK_TO.to_bytes(1, byteorder), (ring_addr, ring_port))
        sleep(4)
        
        for row in method.rows:
          if stop_playing:
            break
          if row.call_go:
            sock.sendto(GO.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_thats_all:
            sock.sendto(THATS_ALL.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_bob:
            sock.sendto(BOB.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_single:
            sock.sendto(SINGLE.to_bytes(1, byteorder), (ring_addr, ring_port))
          if row.call_stand:
            sock.sendto(STAND.to_bytes(1, byteorder), (ring_addr, ring_port))
          stroke_type = "H" if stroke_type == "B" else "B"
          if row.frame_start:
            print("--------------")
          print(stroke_type, end = " ", flush = True)
          position = 1
          for strike in row.bell_order:
            if stop_playing:
              break
            sock.sendto(graphic_show_indicators[strike - 1].to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
            sleep(pause / 2.0)
            print(position, end = " ", flush = True)
            if stroke_type == 'H':
                indicator = backstroke_indicators[strike - 1]
            else:
                indicator = handstroke_indicators[strike - 1]
            sock.sendto(indicator.to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
            if bells[strike - 1]:
              sock.sendto(strike.to_bytes(1, byteorder), (ring_addr, ring_port))
            position = position + 1
            if position > method.bells:
              position = 1
              print("")
            sleep(pause / 2.0)
            sock.sendto(graphic_clear_indicators[strike - 1].to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
          if stroke_type == 'B':
            # Hand stroke lead pause
            sleep(pause)
            
    t = None
    while True:
        command = conn.recv().split(",")
        if command[0] == "Exit":
            stop_playing = True
            if t and t.is_alive():
                t.join()
            break
        elif command[0] == "Start":
            stop_playing = False
            if method:
                t = Thread(target = play, args = (ring_port,))
                t.start()
        elif command[0] == "Stop":
            stop_playing = True
            if t and t.is_alive():
                t.join()
        elif command[0] == 'Pace':
            pace = float(command[1])
            if method:
                pause = pace / method.bells
            else:
                pause = pace / MAX_BELLS
        elif command[0] == "Load":
            method = Method(app_path + '/data/' + command[1] + '.mdf', cover = (command[2] == 'cover'), intro_courses = int(command[3]), method_courses = int(command[4]))
            pause = pace / method.bells
        elif command[0] == "Play":
            bell = int(command[1])
            bells[bell - 1] = command[2] == "True"
