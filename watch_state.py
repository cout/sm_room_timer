#!/usr/bin/env python3

from retroarch.network_command_socket import NetworkCommandSocket
from state import State
from rooms import Rooms
from doors import Doors

import argparse
import time
import sys

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  sock = NetworkCommandSocket()

  initial_door_ids = { key: True for key in doors.by_id.keys() }

  current_room = None
  last_room = None
  prev_state = None

  while True:
    state = State.read_from(sock, rooms, doors)
    state.event_flags = '%x' % state.event_flags
    print("\033[2J")
    print("\033[H")
    for k,v in state.__dict__.items():
      if prev_state and getattr(prev_state, k) != v:
        print('%s: \033[1m%s\033[m%s' % (k, repr(v), ' '*40))
      else:
        print('\033[2m%s: %s\033[m%s' % (k, repr(v), ' '*40))
    prev_state = state
