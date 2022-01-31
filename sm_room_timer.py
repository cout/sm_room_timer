#!/usr/bin/env python3

import datetime
import time
import argparse
import csv
import os.path
import sys
import tempfile
import math

from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from frame_count import FrameCount
from transition import TransitionId, TransitionTime, Transition
from history import History, read_history_file
from route import Route, DummyRoute
from state import State, NullState
from rebuild_history import need_rebuild, rebuild_history

class Store(object):
  def __init__(self, rooms, doors, route, filename=None):
    if filename is not None and os.path.exists(filename):
      self.history = read_history_file(filename, rooms, doors)
    else:
      self.history = History()

    self.route = route
    for tid in self.history:
      self.route.record(tid)
      if route.complete: break

    print('Route is %s' % ('complete' if route.complete else 'incomplete'))

    self.extra_file = open('extra.csv', 'a')
    self.extra_writer = csv.writer(self.extra_file)

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
    self.extra_writer.writerow((
      '%04x' % transition.id.room.room_id,
      '%04x' % transition.id.exit_room.room_id,
      transition.id.room,
      transition.id.exit_room,
      transition.time.realtime_door,
      transition.time.door,
      transition.time.realtime_door - transition.time.door,
      ))
    self.extra_file.flush()

    if not self.route.complete:
      self.route.record(transition.id)
      if self.route.complete:
        print('GG! Route is complete!')
    elif transition.id not in self.route:
      print('Ignoring transition (not in route)')
      return None

    attempts = self.history.record(transition)
    # history_report(self.history)

    if self.writer is not None:
      self.writer.writerow(transition.as_csv_row())
      self.file.flush()

    return attempts

  def room_reset(self, reset_id):
    # TODO: Verify entry door is in the route before recording reset

    self.history.record_reset(reset_id)

    # TODO: Write reset to history file

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
    self.is_preset = state.game_state == 'NormalGameplay' and state.last_realtime_room == FrameCount(0) and state.room.name != 'Ceres Elevator'
    self.is_loading_preset = prev_state.ram_load_preset != state.ram_load_preset and state.ram_load_preset != 0
    self.door_changed = prev_state.door != state.door
    self.game_state_changed = prev_state.game_state != state.game_state
    self.is_playing = state.game_state_id >= 0x08 and state.game_state_id <= 0x18

  def __repr__(self):
    return "State(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

class RoomTimer(object):
  def __init__(self, rooms, doors, store, sock, debug_log=None, verbose=False):
    self.rooms = rooms
    self.doors = doors
    self.store = store
    self.sock = sock
    self.debug_log = debug_log
    self.verbose = verbose

    self.current_room = NullRoom
    self.last_room = NullRoom
    self.most_recent_door = NullDoor
    self.last_most_recent_door = NullDoor
    self.ignore_next_transition = False
    self.prev_state = NullState

  def log_debug(self, *args):
    if self.debug_log:
      print(*args, file=self.debug_log)

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
      if state.door.is_unknown:
        print("Unknown door %04x from %s (%04x) to %s (%04x)" % (
          state.door.door_id, self.current_room,
          self.current_room.room_id, state.room,
          state.room.room_id))
      self.last_room = self.current_room
      self.current_room = state.room
      self.last_most_recent_door = self.most_recent_door
      self.most_recent_door = state.door

    if change.is_reset:
      self.handle_reset(state, change)

    # When the game state changes to NormalGameplay, we can be sure we
    # are no longer in the door transition.  Record the transition.
    # Note that we use the current state for the room times, because we
    # might not have captured the exact frame where the room times
    # changed, but once the game state has changed, we can be sure the
    # state has the room times.
    elif change.transition_finished:
      if state.seg_rt < self.prev_state.seg_rt:
        print("Ignoring transition (segment timer went backward)")
      elif state.last_door_lag_frames == FrameCount(0):
        print("Transition not yet finished? (door time is 0.00)")
      else:
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

    if change.is_playing and change.is_program_start and change.is_preset:
      print("Ignoring next transition due to starting in a room where a preset was loaded")
      self.ignore_next_transition = True

    elif change.is_playing and change.is_reset and change.is_preset:
      print("Ignoring next transition due to loading a preset")
      self.ignore_next_transition = True

    self.prev_state = state

  def log_state_changes(self, change):
    state_changed = False

    if change.is_program_start:
      self.log_verbose("Starting in room %s at %s, door=%s" % (
        change.state.room, change.state.igt, change.state.door))
    elif change.is_room_change and change.transition_finished:
      self.log_verbose("Transition to %s (%x) at %s using door %s" % (
          change.state.room, change.state.room.room_id,
          change.state.igt, change.state.door))
    elif change.reached_ship:
      self.log_verbose("Reached ship at %s" % (change.state.igt))
      state_changed = True
    elif change.is_room_change:
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
      self.log_debug("%s Game state changed to %s at %s" % (time.time(), change.state.game_state, change.state.igt))
      state_changed = True

    if state_changed:
      self.log_debug("Previous state:", self.prev_state)
      self.log_debug("State:", change.state)
      self.log_debug("Changes:", change)
      self.log_debug()

  def handle_reset(self, state, change):
    # TODO: Can we differentiate between a reset due to failing the room
    # and a reset due to wanting to try the previous room again?

    if not self.ignore_next_transition:
      try:
        reset_id = TransitionId(self.last_room, self.last_most_recent_door,
            NullDoor, state.items, state.beams)
        self.store.room_reset(reset_id)
      except Exception as exc:
        print("Exception handing reset:")
        print("  state=%s" % state)
        print("  change=%s" % change)
        print("  exc=%s" % exc)

    # If we reset state to the middle of a door transition, then we
    # don't want to count the next transition, because it has already
    # been counted.
    if state.game_state == 'DoorTransition':
      self.ignore_next_transition = True

    if change.transition_finished:
      print("Reset detected during door transition")

  def handle_transition(self, state):
    if self.last_room is not self.last_most_recent_door.exit_room:
      print("Ignoring transition (entry door leads to %s, not %s)" %
          (self.last_most_recent_door.exit_room, self.last_room))
      return

    if self.last_room is not self.most_recent_door.entry_room:
      print("Ignoring transition (exit door is located in room %s, not %s)" %
          (self.most_recent_door.entry_room, self.last_room))
      return

    ts = datetime.datetime.now()
    try:
      transition_id = TransitionId(
          self.last_room, self.last_most_recent_door,
          self.most_recent_door, state.items, state.beams)
    except Exception as exc:
      print("Exception constructing transition id:")
      print("  state=%s" % state)
      print("  change=%s" % change)
      print("  exc=%s" % exc)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, state.last_door_lag_frames,
        state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    if attempts: self.log_transition(transition, attempts)

  def handle_escaped_ceres(self, state):
    ts = datetime.datetime.now()
    transition_id = TransitionId(
        state.room, state.door, self.doors.from_id(0x88FE),
        state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, FrameCount(0), state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    if attempts: self.log_transition(transition, attempts)

  def handle_reached_ship(self, state):
    ts = datetime.datetime.now()
    transition_id = TransitionId(
        state.room, state.door,
        NullDoor, state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, FrameCount(0), state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    attempts = self.store.transitioned(transition)
    if attempts: self.log_transition(transition, attempts)

  def log_transition(self, transition, attempts):
    if self.verbose:
      # When verbose logging is enabled, we  want to minimize the number
      # of lines displayed
      # TODO: Colorize this the same as below
      print('%s #%s:' % (transition.id, len(attempts)))
    else:
      # Without verbose logging, we want to minimize the width of the
      # lines we are printing
      reset_id = TransitionId(transition.id.room, transition.id.entry_door,
          NullDoor, transition.id.items, transition.id.beams)
      resets = self.store.history.reset_count(reset_id)
      completions = self.store.history.completed_count(transition.id)
      denom = float(resets + completions)
      success_rate = int(float(completions) / denom * 100) if denom != 0 else 0
      print('Room: \033[1m%s\033[m (#%d, %d%% success)' %
          (transition.id.room, len(attempts), success_rate))
      print('Entered from: %s' % transition.id.entry_room)
      print('Exited to: %s' % transition.id.exit_room)

    print('Game: %s' % self.colorize(transition.time.gametime, attempts.gametimes))
    print('Real: %s' % self.colorize(transition.time.realtime, attempts.realtimes))
    print('Lag:  %s' % self.colorize(transition.time.roomlag, attempts.roomlagtimes))
    print('Door: %s' % self.colorize(transition.time.door, attempts.doortimes))
    print('RD:   %s (%s)' % (transition.time.realtime_door, transition.time.realtime_door - transition.time.door))
    print('')

  def colorize(self, ttime, atimes):
    mean = atimes.mean()
    best = atimes.best()
    prev_best = atimes.prev_best()
    p25 = atimes.percentile(25)
    p50 = atimes.median()
    p75 = atimes.percentile(75)

    color = 8
    if ttime <= best:
      color = 214
    elif ttime <= p25:
      color = 40
    elif ttime <= p50:
      color = 148
    elif ttime <= p75:
      color = 204
    else:
      color = 196

    if ttime == best and prev_best != FrameCount.max:
      stats = 'avg %s, median %s, previous best %s' % (mean, p50, prev_best)
    else:
      stats = 'avg %s, median %s, best %s' % (mean, p50, best)

    return "\033[38;5;%sm%s\033[m (%s)" % (color, ttime, stats)

def backup_and_rebuild(rooms, doors, filename):
  with tempfile.NamedTemporaryFile(prefix='.%s' % filename, delete=False) as tmp:
    unlink = True

    try:
      rebuild_history(
          rooms=rooms, doors=doors, input_filenames=[filename],
          output_filename=tmp.name)
      backup_filename = '%s.bk' % filename
      idx = 0
      while os.path.exists(backup_filename):
        idx += 1
        backup_filename = '%s.bk%s' % (filename, idx)

      print("Rebuilt history; original file is saved in %s" % backup_filename)
      os.rename(filename, backup_filename)
      os.rename(tmp.name, filename)
      unlink = False

    finally:
      if unlink: os.unlink(tmp.name)

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--debug', dest='debug', action='store_true')
  parser.add_argument('--debug-log', dest='debug_log_filename')
  parser.add_argument('--verbose', dest='verbose', action='store_true')
  parser.add_argument('--usb2snes', action='store_true')
  parser.add_argument('--route', action='store_true')
  parser.add_argument('--rebuild', action='store_true')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  route = Route() if args.route else DummyRoute()

  if args.filename and need_rebuild(args.filename):
    if not args.rebuild:
      print("File needs to be rebuilt before it can be used; run rebuild_history.py or pass --rebuild to this script.")
      sys.exit(1)

    backup_and_rebuild(rooms, doors, args.filename)

  store = Store(rooms, doors, route, args.filename)

  if args.usb2snes:
    sock = WebsocketClient('sm_room_timer')
  else:
    sock = NetworkCommandSocket()

  if args.debug_log_filename:
    debug_log = open(args.debug_log_filename, 'a')
    verbose = True
  elif args.debug:
    debug_log = sys.stdout
    verbose = True
  else:
    debug_log = None
    verbose = args.verbose

  timer = RoomTimer(rooms, doors, store, sock, debug_log=debug_log, verbose=verbose)

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
