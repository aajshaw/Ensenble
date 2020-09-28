from multiprocessing import Process, Pipe
import socket
from sys import byteorder
from Ringers import ringers
from Methods import methods, Method
from Strike import ring_bells
from Config import Config
import PySimpleGUI as sg
from PIL import Image
from threading import Thread

# Load the absolute minimum data for a method
class PlayableMethod():
    def __init__(self, method):
        self.name = method
        self.method = Method('./data/' + self.name + '.mdf', load_rows = False)
    
    def __str__(self):
        return self.name

# Set the bell checkboxes and associated text to show which bells
# are going to be in use in a particular method
def manage_bell_selection(checkboxes, number_of_bells, add_cover):
    for ndx in range(len(checkboxes)):
        checkboxes[ndx].update(value = False, text = str(ndx + 1) + '     ', disabled = False)
        bell_controller(ndx + 1, False)
    checkboxes[0].update(text = 'Treble')
    nob = number_of_bells
    # We don't usually have a cover bell if the number of moving bells
    # in the methjod is even
    if nob % 2 != 0 and add_cover and nob < MAX_BELLS:
        nob += 1
    checkboxes[nob - 1].update(text = 'Tenor ')
    for ndx in range(nob, len(checkboxes)):
        checkboxes[ndx].update(disabled = True)

# Tell the method conducting and switch sensor processes that they should
# start doing their thing
def start():
    parent_method.send("Start")
    parent_ringer.send("Start")
    
    return True

# Tell the method conducting and switch sensor processes that the should
# go to sleep
def stop():
    parent_method.send("Stop")
    parent_ringer.send("Stop")

    # Yep, definitly want to return False
    return False

# Setup all of the PySimpleGUI stuff for the individual bell ropes
def setup_bells():
    bell_checkboxes = []
    bell_ropes = []
    bell_pull_indicators = []

    for ndx in range(MAX_BELLS):
        bell_checkboxes.append(sg.Checkbox(str(ndx + 1) + '     ', key = '-BELL_' + str(ndx + 1) + '-', enable_events = True))
        bell_ropes.append(sg.Image(filename = './data/SmallSally.png'))
        bell_pull_indicators.append(sg.Image(filename = './data/IndicatorBlank.png'))
    
    return bell_checkboxes, bell_ropes, bell_pull_indicators

# Put all of the bell ropes into a series of PYSimpleGUI Columns
def setup_bell_selection(bell_pull_indicators, bell_ropes, bell_checkboxes):
    bell_selection = []
    
    for ndx in range(MAX_BELLS):
        bell_selection.append(sg.Column([[bell_pull_indicators[ndx]], [bell_ropes[ndx]], [bell_checkboxes[ndx]]], element_justification = 'c'))

    return bell_selection

# Tell the method conductor and switch sensor processes which bells they are (not) controlling
def bell_controller(bell_id, selected):
    parent_method.send("Play," + str(bell_id) + "," + ("False" if selected else "True"))
    parent_ringer.send("ListenFor," + str(bell_id) + "," + ("True" if selected else "False"))

# What should be displayed in the GUI is controlled as a set of bit flags
# sent by the method conductor process, calculated once and used many times
def bell_indicators():
    INDICATE_BELL_HANDSTROKE = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_bell') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_BACKSTROKE = INDICATE_BELL_HANDSTROKE + \
                               (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_stroke_shift'))
    INDICATE_BELL_GRAPHIC_CLEAR = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_graphic') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_type_shift')
    INDICATE_BELL_GRAPHIC_SHOW = INDICATE_BELL_GRAPHIC_CLEAR + \
                                 (config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_mask') << config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_graphic_shift'))
    INDICATE_BELL_NUMBER_SHIFT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_bell_number_shift')
    hand = {}
    back = {}
    graphic_show = {}
    graphic_clear = {}
    for ndx in range(config.getint('BELLS', 'bells')):
        hand[INDICATE_BELL_HANDSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        back[INDICATE_BELL_BACKSTROKE | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        graphic_show[INDICATE_BELL_GRAPHIC_SHOW | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
        graphic_clear[INDICATE_BELL_GRAPHIC_CLEAR | (ndx << INDICATE_BELL_NUMBER_SHIFT)] = ndx
    
    return hand, back, graphic_show, graphic_clear

# Set (stand) all bells
def set_to_handstroke(ropes):
    for ndx in range(MAX_BELLS):
        ropes[ndx].update(filename = './data/SmallSally.png')

# Listen on the socket bound to the method conductor process and change the
# display to be in line with the bells being rung
def gui_events_listener(addr, port, window):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((addr, port))
    EXIT = config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_exit')
    handstroke_indicators, backstroke_indicators, graphic_show_indicators, graphic_clear_indicators = bell_indicators()

    while True:
        data, from_addr = sock.recvfrom(8)
        command = int.from_bytes(data, byteorder)
        if command in handstroke_indicators:
            window.write_event_value('-INDICATE_BELL_HANDSTROKE-', str(handstroke_indicators[command]))
        elif command in backstroke_indicators:
            window.write_event_value('-INDICATE_BELL_BACKSTROKE-', str(backstroke_indicators[command]))
        elif command in graphic_show_indicators:
            window.write_event_value('-INDICATE_BELL_SHOW_GRAPHIC-', str(graphic_show_indicators[command]))
        elif command in graphic_clear_indicators:
            window.write_event_value('-INDICATE_BELL_CLEAR_GRAPHIC-', str(graphic_clear_indicators[command]))
        elif command == EXIT:
            break
            
if __name__ == '__main__':
    config = Config('bells.ini')
    
    MAX_BELLS = config.getint('BELLS', 'bells')

    # Pipes and sockets that will be used to communicate with the method conductor,
    # switch sensor and bell sound processes
    parent_method, child_method = Pipe()
    parent_ringer, child_ringer = Pipe()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Start the processes and give them the pipe/socket information that will
    # allow them to communicate with each other
    ringer = Process(target = ringers, args = (child_ringer, config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    ringer.start()
    method = Process(target = methods, args = (child_method, config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    method.start()
    bells = Process(target = ring_bells, args = (config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    bells.start()

    # Get a list of the methods that can be played    
    playable = []
    for meth in config.items("METHODS"):
        playable.append(PlayableMethod(meth[1]))

    started = False

    # PySimpleGUI setup
    sg.theme('BlueMono')
    
    bell_checkboxes, bell_ropes, bell_pull_indicators = setup_bells()
    bell_selection = setup_bell_selection(bell_pull_indicators, bell_ropes, bell_checkboxes)
    
    selected_method = None
    add_cover = True
    bong_along = True
    animated_rounds = True
    animated_ropes = True
    
    add_cover_checkbox = sg.Checkbox('Add cover bell', key = '-ADD_COVER-', default = add_cover, enable_events = True)
    courses_spin = sg.Spin(('1', '2', '3', '4'), '1', key = '-COURSES-', enable_events = True)
    intro_spin = sg.Spin(('1', '2', '3', '4'), '1', key = '-INTRO_ROUNDS-', enable_events = True)
    
    layout = [ [sg.Text('Select method'), sg.Combo(playable, key = '-METHOD-', enable_events = True, readonly = True)],
                 [add_cover_checkbox,
                  sg.Checkbox('Bong-along', key = '-BONG_ALONG-', default = bong_along, enable_events = True),
                  sg.Checkbox('Animated ropes', key = '-ANIMATED_ROPES-', default = animated_ropes, enable_events = True)],
               [sg.Text('Set pace of rounds'),
                sg.Slider(key = '-PACE-', range = (2.0, 5.0), default_value = 0.5 * 6, resolution = 0.1, orientation = 'h', enable_events = True),
                sg.Text('Courses'),
                courses_spin,
                sg.Text('Intro rounds'),
                intro_spin],
               [sg.Frame('Select bells to be controlled by buttons', [bell_selection], relief = sg.RELIEF_RAISED, border_width = 2)],
               [sg.Button('Look to'), sg.Button('Stand'), sg.Button('Exit', button_color = ('black','red'))] ]
    
    window = sg.Window('Ringable Ensemble', layout, icon = './ringable_icon.png', font = ('', 20), element_justification = 'c')

    # Start trhe threat that will monitor GUI updates sent from the method
    # conductor process
    gui_events = Thread(target = gui_events_listener, args = (config.get('GUI_EVENT_LISTENER', 'addr'), config.getint('GUI_EVENT_LISTENER', 'port'), window))
    gui_events.start()
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            sock.sendto(config.getint('GUI_EVENT_LISTENER_COMMANDS', 'indicate_exit').to_bytes(1, byteorder), (config.get('GUI_EVENT_LISTENER', 'addr',), config.getint('GUI_EVENT_LISTENER', 'port')))
            break
        elif event.startswith('-BELL'):
            bell_controller(int(event[6:7]), values[event])
        elif event == '-METHOD-':
            started = stop()
            selected_method = values['-METHOD-']
            # If a Minor, Major, etc then no cover
            if selected_method.method.bells % 2 == 0:
                add_cover_checkbox.update(disabled = True)
                add_cover = False
            else:
                add_cover_checkbox.update(disabled = False)
                add_cover = True
            courses_spin.update(value = '1')
            intro_spin.update(value = '1')
            parent_ringer.send("ResetAll")
            manage_bell_selection(bell_checkboxes, selected_method.method.bells, add_cover)
            set_to_handstroke(bell_ropes)
        elif event == '-PACE-':
            parent_method.send("Pace," + str(values['-PACE-']))
        elif event == '-COURSES-':
            started = stop()
        elif event == '-INTRO_ROUNDS-':
            started = stop()
        elif event == 'Look to':
            started = stop()
            set_to_handstroke(bell_ropes)
            request = "Load," + selected_method.name + ","
            if not add_cover:
                request = request + "no"
            request = request + "cover," + values['-INTRO_ROUNDS-'] + ',' + values['-COURSES-']
            parent_method.send(request)
            started = start()
        elif event == 'Stand':
            started = stop()
            set_to_handstroke(bell_ropes)
        elif event == '-ADD_COVER-':
            add_cover = values['-ADD_COVER-']
            started = stop()
            if selected_method:
                manage_bell_selection(bell_checkboxes, selected_method.method.bells, add_cover)
            set_to_handstroke(bell_ropes)
        elif event == '-INDICATE_BELL_HANDSTROKE-':
            if started and animated_ropes:
                bell_ropes[int(values['-INDICATE_BELL_HANDSTROKE-'])].update(filename = './data/SmallSally.png')
        elif event == '-INDICATE_BELL_BACKSTROKE-':
            if started and animated_ropes:
                bell_ropes[int(values['-INDICATE_BELL_BACKSTROKE-'])].update(filename = './data/SmallTail.png')
        elif event == '-INDICATE_BELL_SHOW_GRAPHIC-':
            if started and bong_along:
                bell_pull_indicators[int(values['-INDICATE_BELL_SHOW_GRAPHIC-'])].update(filename = './data/IndicatorBell.png')
        elif event == '-INDICATE_BELL_CLEAR_GRAPHIC-':
            bell_pull_indicators[int(values['-INDICATE_BELL_CLEAR_GRAPHIC-'])].update(filename = './data/IndicatorBlank.png')
        elif event == '-BONG_ALONG-':
            bong_along = values['-BONG_ALONG-']
        elif event == '-ANIMATED_ROPES-':
            animated_ropes = values['-ANIMATED_ROPES-']

    # Wait for the GUI event monitor thread to shutdown
    gui_events.join()
    
    window.close()

    # Shut down all of the sub-processes
    parent_method.send("Exit")
    method.join()
    
    parent_ringer.send("Exit")
    ringer.join()
    
    sock.sendto(config.getint('STRIKE_COMMANDS', 'exit').to_bytes(1, byteorder), (config.get('STRIKE', 'addr'), config.getint('STRIKE', 'port')))
    bells.join()
