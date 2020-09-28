from gpiozero import Button
import socket
from multiprocessing import Pipe
from sys import byteorder
from datetime import timedelta, datetime as dt

def ringers(conn, ring_addr, ring_port):
    bells = {}
    BELL_DEBOUNCE = timedelta(seconds = 0.25)

    class Bell:
        def __init__(self, bell_id, pin_id, ring_socket, ring_port):
            if pin_id > 0:
                self.button = Button(pin_id, bounce_time = None)
                self.button.when_pressed = self.ring
            self.bell_id = bell_id
            self.last_ring = dt.now()
            self.ring_socket = ring_socket
            self.ring_port = ring_port
            self.enabled = False
        
        def enable(self, flag):
            self.enabled = flag

        def ring(self):
            if self.enabled:
                now = dt.now()
                if now - self.last_ring >= BELL_DEBOUNCE:
                    self.last_ring = now
                    self.ring_socket.sendto(self.bell_id.to_bytes(1, byteorder), (ring_addr, ring_port))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    bells[1] = Bell(1, 12, sock, ring_port)
    bells[2] = Bell(2, 13, sock, ring_port)
    bells[3] = Bell(3, 16, sock, ring_port)
    bells[4] = Bell(4, 5, sock, ring_port)
    bells[5] = Bell(5, 20, sock, ring_port)
    bells[6] = Bell(6, 6, sock, ring_port)
    bells[7] = Bell(7, -1, sock, ring_port)
    bells[8] = Bell(8, -1, sock, ring_port)

    while True:
        command = conn.recv().split(',')
        if command[0] == "Exit":
            break
        elif command[0] == "Start":
            pass
        elif command[0] == "Stop":
            pass
        elif command[0] == "ListenFor":
            listen = int(command[1])
            bells[listen].enable(command[2] == "True")
        elif command[0] == "ResetAll":
            for b in bells:
                bells[b].enable(False)
