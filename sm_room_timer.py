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
from state import State, NullState

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

  def transitioned(self, transition):
    attempts = self.history.record(transition)
    # history_report(self.history)

    if self.writer is not None:
      self.writer.writerow(transition.as_csv_row())
      self.file.flush()

    return attempts

  def close(self):
    self.file.close()

class StateChange(object):
  def __init__(self, prev_state, state, current_room):
    self.prev_state = prev_state
    self.state = state
    self.is_room_change = state.game_state == 'NormalGameplay' and current_room is not state.room
    self.is_program_start = self.is_room_change and current_room is NullRoom
    self.transition_finished = state.game_state == 'NormalGameplay' and prev_state.game_state == 'DoorTransition'
    self.escaped_ceres = state.game_state == 'StartOfCeresCutscene' and prev_state.game_state == 'NormalGameplay' and state.room.name == 'Ceres Elevator'
    self.reached_ship = (state.event_flags & 0x40) > 0 and prev_state.ship_ai != state.ship_ai and state.ship_ai == 0xaa4f
    self.is_reset = state.igt < prev_state.igt
    self.is_preset = state.last_realtime_room == FrameCount(0) and state.room.name != 'Ceres Elevator'
    self.is_loading_preset = prev_state.ram_load_preset != state.ram_load_preset and state.ram_load_preset != 0
    self.door_changed = prev_state.door != state.door
    self.game_state_changed = prev_state.game_state != state.game_state

  def __repr__(self):
    return "State(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

class RoomTimer(object):
  def __init__(self, rooms, doors, store, debug=False, verbose=False):
    self.rooms = rooms
    self.doors = doors
    self.store = store
    self.debug = debug
    self.verbose = verbose

    self.sock = NetworkCommandSocket()
    self.current_room = NullRoom
    self.last_room = NullRoom
    self.most_recent_door = NullDoor
    self.last_most_recent_door = NullDoor
    self.ignore_next_transition = False
    self.prev_state = NullState

  def log_debug(self, *args):
    if self.debug:
      print(*args)

  def log_verbose(self, *args):
    if self.verbose:
      print(*args)

  def poll(self):
    state = State.read_from(self.sock, self.rooms, self.doors)
    change = StateChange(self.prev_state, state, self.current_room)

    self.log_state_changes(change)

    # When the room changes (and we're not in demo mode), we want to
    # take note.  Most of the time, the previous game state was
    # doorTransition, and we'll record the transition below.
    #
    # TODO: if we just started the room timer, or if we just loaded a
    # preset, then we won't know wha the previous room was.  I think
    # that would require changes to the practice ROM.
    if change.is_room_change or change.reached_ship:
      self.last_room = self.current_room
      self.current_room = state.room
      self.last_most_recent_door = self.most_recent_door
      self.most_recent_door = state.door

    # If we reset state to the middle of a door transition, then we
    # don't want to count the next transition, because it has already
    # been counted.
    if change.is_reset and state.game_state == 'DoorTransition':
      self.ignore_next_transition = True

    # When the game state changes to NormalGameplay, we can be sure we
    # are no longer in the door transition.  Record the transition.
    # Note that we use the current state for the room times, because we
    # might not have captured the exact frame where the room times
    # changed, but once the game state has changed, we can be sure the
    # state has the room times.
    if change.transition_finished:
      if not self.ignore_next_transition:
        self.handle_transition(state)
      self.ignore_next_transition = False

    if change.escaped_ceres:
      self.handle_escaped_ceres(state)

    # When Samus reaches the ship and the cutscent starts, it is a
    # special case, since there is no real exit door.  The room times
    # are updated after the game state changes to EndCutscene, but by
    # tha time the counters have advanced too far, and the door timer is
    # completely wrong (there is no door).
    if change.reached_ship:
      self.handle_reached_ship(state)

    if change.is_loading_preset:
      # TODO: This does not always detect loading of a preset, and when
      # it does detect it, we should ignore all transitions until the
      # next IGT reset is detected
      print("Loading preset %04x; next transition may be wrong" % state.ram_load_preset)

    if change.is_program_start and change.is_preset:
      print("Ignoring next transition due to starting in a room where a preset was loaded")
      self.ignore_next_transition = True

    elif change.is_reset and change.is_preset:
      print("Ignoring next transition due to loading a preset")
      self.ignore_next_transition = True

    self.prev_state = state

  def log_state_changes(self, change):
    state_changed = False

    if change.is_room_change:
      if change.is_program_start:
        self.log_verbose("Starting in room %s at %s, door=%s" % (
          change.state.room, change.state.igt, change.state.door))
      elif change.transition_finished:
        self.log_verbose("Transition to %s (%x) at %s using door %s" % (
            change.state.room, change.state.room.room_id,
            change.state.igt, change.state.door))
      elif change.reached_ship:
        self.log_verbose("Reached ship at %s" % (change.state.igt))
      else:
        self.log_verbose("Room changed to %s (%x) at %s without using a door" % (
          change.state.room, change.state.room.room_id,
          change.state.igt))
      state_changed = True

    if change.is_reset:
      self.log_verbose("Reset detected to %s" % change.state.igt)
      state_changed = True

    if change.door_changed:
      self.log_debug("Door changed to %s at %s" % (change.state.door, change.state.igt))
      state_changed = True

    if change.game_state_changed:
      self.log_debug("Game state changed to %s at %s" % (change.state.game_state, change.state.igt))
      state_changed = True

    if state_changed:
      self.log_debug("Previous state:", self.prev_state)
      self.log_debug("State:", change.state)
      self.log_debug("Changes:", change)
      self.log_debug()

  def handle_transition(self, state):
    if self.last_room is not self.last_most_recent_door.exit_room:
      print("Ignoring transition (entry door leads to %s, not %s)" %
          (self.last_most_recent_door.exit_room, self.last_room))
      return

    if self.last_room is not self.most_recent_door.entry_room:
      print("Ignoring transition (exit door is located in room %s, not %s)" %
          (self.most_recent_door.entry_room, self.last_room))
      return

    transition_id = TransitionId(
        self.last_room, self.last_most_recent_door,
        self.most_recent_door, state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, state.last_door_lag_frames)
    transition = Transition(transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    self.log_transition(transition, attempts)

  def handle_escaped_ceres(self, state):
    # TODO: use lag counter or use realtime - TC?
    transition_id = TransitionId(
        state.room, state.door, self.doors.from_id(0x88FE),
        state.items, state.beams)
    transition_time = TransitionTime(
        state.gametime_room, state.realtime_room,
        state.lag_counter, FrameCount(0))
    transition = Transition(transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    self.log_transition(transition, attempts)

  def handle_reached_ship(self, state):
    # TODO: use lag counter or use realtime - TC?
    transition_id = TransitionId(
        state.room, state.door,
        NullDoor, state.items, state.beams)
    transition_time = TransitionTime(
        state.gametime_room, state.realtime_room,
        state.lag_counter, FrameCount(0))
    transition = Transition(transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    self.log_transition(transition, attempts)

  def log_transition(self, transition, attempts):
    if self.verbose:
      # When verbose logging is enabled, we  want to minimize the number
      # of lines displayed
      # TODO: Colorize this the same as below
      print('%s #%s:' % (transition.id, len(attempts)))
    else:
      # Without verbose logging, we want to minimize the width of the
      # lines we are printing
      print('Room: \033[1m%s\033[m' % transition.id.room)
      print('Entered from: %s' % transition.id.entry_room)
      print('Exited to: %s' % transition.id.exit_room)

    print('Game: %s' % self.colorize(transition.time.gametime, attempts.gametimes))
    print('Real: %s' % self.colorize(transition.time.realtime, attempts.realtimes))
    print('Lag:  %s' % self.colorize(transition.time.roomlag, attempts.roomlagtimes))
    print('Door: %s' % self.colorize(transition.time.door, attempts.doortimes))
    print('')

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


def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--debug', dest='debug', action='store_true')
  parser.add_argument('--verbose', dest='verbose', action='store_true')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  store = Store(rooms, doors, args.filename)
  timer = RoomTimer(rooms, doors, store, debug=args.debug, verbose=(args.verbose or args.debug))

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
