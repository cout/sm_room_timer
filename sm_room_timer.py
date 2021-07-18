#!/usr/bin/env python3

import datetime
import time
import argparse
import csv
import os.path

from retroarch.network_command_socket import NetworkCommandSocket
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from frame_count import FrameCount
from transition import TransitionId, TransitionTime, Transition
from history import History, read_history_file
from state import State

class Store(object):
  def __init__(self, rooms, doors, filename=None):
    if filename is not None and os.path.exists(filename):
      self.history = read_history_file(filename, rooms, doors)
    else:
      self.history = History()

    if filename is not None:
      self.file = open(filename, 'a')
      self.writer = csv.writer(self.file)
      # TODO: this incorrectly appends headers to a file that only has a header line
      if len(self.history) == 0:
        print(','.join(Transition.csv_headers()), file=self.file)
    else:
      self.file = None
      self.writer = None

  def colorize(self, ttime, atimes):
    p0 = atimes.best()
    p25 = atimes.percentile(25)
    p50 = atimes.median()
    p75 = atimes.percentile(75)

    color = 8
    if ttime <= p0:
      color = 214
    elif ttime <= p25:
      color = 40
    elif ttime <= p50:
      color = 148
    elif ttime <= p75:
      color = 204
    else:
      color = 196

    return "\033[38;5;%sm%s\033[m (%s)" % (color, ttime, atimes)

  def transitioned(self, transition):
    attempts = self.history.record(transition)
    # history_report(self.history)

    if self.writer is not None:
      self.writer.writerow(transition.as_csv_row())
      self.file.flush()

    print('%s #%s:' % (transition.id, len(attempts)))
    print('Game: %s' % self.colorize(transition.time.gametime, attempts.gametimes))
    print('Real: %s' % self.colorize(transition.time.realtime, attempts.realtimes))
    print('Lag:  %s' % self.colorize(transition.time.roomlag, attempts.roomlagtimes))
    print('Door: %s' % self.colorize(transition.time.door, attempts.doortimes))
    print('')

  def close(self):
    self.file.close()

class RoomTimer(object):
  def __init__(self, rooms, doors, store):
    self.sock = NetworkCommandSocket()
    self.rooms = rooms
    self.doors = doors
    self.store = store
    self.current_room = NullRoom
    self.last_room = NullRoom
    self.most_recent_door = NullDoor
    self.last_most_recent_door = NullDoor
    self.ignore_next_transition = False
    self.prev_state = State(
        game_state=None,
        igt=FrameCount(0),
        ram_load_preset=None)

  def poll(self):
    state = State.read_from(self.sock, self.rooms, self.doors)

    if self.prev_state.ram_load_preset != state.ram_load_preset and state.ram_load_preset != 0:
      # TODO: This does not always detect loading of a preset, and when
      # it does detect it, we should ignore all transitions until the
      # next IGT reset is detected
      print("Loading preset %04x; the next transition may be wrong" % state.ram_load_preset)

    if self.prev_state.game_state != state.game_state:
      print("Game state changed to %s" % state.game_state)

    # When the room changes (and we're not in demo mode), we want to
    # take note.  Most of the time, the previous game state was
    # doorTransition, and we'll record the transition below.
    #
    # TODO: if we just started the room timer, or if we just loaded a
    # preset, then we won't know wha the previous room was.  I think
    # that would require changes to the practice ROM.
    if state.game_state == 'normalGameplay' and self.current_room is not state.room:
      if self.current_room is NullRoom:
        print("Starting in room %s at %s, door=%s" % (state.room, state.igt, state.door))
        print()
      else:
        print("Transition to %s (%x) at %s using door %s" % (state.room, state.room.room_id, state.igt, state.door))
      self.last_room = self.current_room
      self.current_room = state.room
      self.last_most_recent_door = self.most_recent_door
      self.most_recent_door = state.door

    # Check in-game-time to see if we reset state.  This also catches
    # when a preset is loaded, because loading a preset resets IGT to
    # zero.
    if state.igt < self.prev_state.igt:
      # If we reset state to the middle of a door transition, then we
      # don't want to count the next transition, because it has already
      # been counted.
      print("Reset detected to %s" % state.igt)
      if state.game_state == 'doorTransition':
        self.ignore_next_transition = True

    if self.prev_state.game_state == 'doorTransition' and state.game_state == 'normalGameplay':
      if not self.ignore_next_transition:
        self.handle_transition(state)
      self.ignore_next_transition = False

    self.prev_state = state

  def handle_transition(self, state):
    transition_id = TransitionId(
        self.last_room, self.last_most_recent_door,
        self.most_recent_door, state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, state.last_door_lag_frames)
    transition = Transition(transition_id, transition_time)
    self.store.transitioned(transition)

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  store = Store(rooms, doors, args.filename)
  timer = RoomTimer(rooms, doors, store)

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
