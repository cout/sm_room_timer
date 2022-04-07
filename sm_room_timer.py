#!/usr/bin/env python3

import datetime
import time
import argparse
import csv
import os.path
import sys
import tempfile

from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from frame_count import FrameCount
from transition import TransitionId, TransitionTime, Transition
from transition_log import read_transition_log, FileTransitionLog, NullTransitionLog
from history import History
from route import Route, DummyRoute
from state import State, NullState
from rebuild_history import need_rebuild, rebuild_history

class RoomTimeTracker(object):
  def __init__(self, history, transition_log, route,
      on_new_room_time=lambda *args, **kwargs: None):
    self.history = history
    self.route = route
    self.transition_log = transition_log

    self.on_new_room_time = on_new_room_time

  def transitioned(self, transition):
    if not self.route.complete:
      self.route.record(transition.id)
      if self.route.complete:
        print('GG! Route is complete!')
    elif transition.id not in self.route:
      print('Ignoring transition (not in route):', transition.id)
      return None

    attempts = self.history.record(transition)

    self.transition_log.write_transition(transition)

    self.on_new_room_time(transition, attempts, self)

  def room_reset(self, reset_id):
    # TODO: Verify entry door is in the route before recording reset

    self.history.record_reset(reset_id)

    # TODO: Write reset to history file

  def close(self):
    self.transition_log.close()

class StateChange(object):
  def __init__(self, prev_state, state, current_room):
    self.prev_state = prev_state
    self.state = state
    self.is_room_change = state.game_state == 'NormalGameplay' and current_room is not state.room
    self.is_program_start = self.is_room_change and current_room is NullRoom
    self.transition_finished = state.game_state == 'NormalGameplay' and prev_state.game_state == 'DoorTransition'
    self.escaped_ceres = state.game_state == 'StartOfCeresCutscene' and prev_state.game_state == 'NormalGameplay' and state.room.name == 'Ceres Elevator'
    self.reached_ship = state.reached_ship and not prev_state.reached_ship
    self.is_reset = state.igt < prev_state.igt
    self.is_preset = state.game_state == 'NormalGameplay' and state.last_realtime_room == FrameCount(0) and state.room.name != 'Ceres Elevator'
    self.is_loading_preset = prev_state.ram_load_preset != state.ram_load_preset and state.ram_load_preset != 0
    self.door_changed = prev_state.door != state.door
    self.game_state_changed = prev_state.game_state != state.game_state
    self.is_playing = state.game_state_id >= 0x08 and state.game_state_id <= 0x18

  def __repr__(self):
    return "StateChange(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  def description(self):
    changes = [ ]

    if self.is_program_start:
      changes.append("Starting in room %s at %s, door=%s" % (
        self.state.room, self.state.igt, self.state.door))
    elif self.is_room_change and self.transition_finished:
      changes.append("Transition to %s (%x) at %s using door %s" % (
          self.state.room, self.state.room.room_id,
          self.state.igt, self.state.door))
    elif self.reached_ship:
      changes.append("Reached ship at %s" % (self.state.igt))
    elif self.is_room_change:
      changes.append("Room changed to %s (%x) at %s without using a door" % (
        self.state.room, self.state.room.room_id,
        self.state.igt))

    if self.is_reset:
      changes.append("Reset detected to %s" % self.state.igt)

    if self.door_changed:
      changes.append("Door changed to %s at %s" % (self.state.door, self.state.igt))

    if self.game_state_changed:
      changes.append("Game state changed to %s at %s" % (
        self.state.game_state, self.state.igt))

    return changes

class RoomTimer(object):
  def __init__(self, logger, rooms, doors, sock,
      on_transitioned=lambda *args, **kwargs: None,
      on_state_change=lambda *args, **kwargs: None,
      on_reset=lambda *args, **kwargs: None):
    self.logger = logger
    self.rooms = rooms
    self.doors = doors
    self.sock = sock

    self.on_transitioned = on_transitioned
    self.on_state_change = on_state_change
    self.on_reset = on_reset

    self.current_room = NullRoom
    self.last_room = NullRoom
    self.most_recent_door = NullDoor
    self.last_most_recent_door = NullDoor
    self.ignore_next_transition = False
    self.prev_state = NullState

  def log(self, *args):
    self.logger.log(*args)
    self.log_debug(*args)

  def log_debug(self, *args):
    self.logger.log_debug(*args)

  def log_verbose(self, *args):
    self.logger.log_verbose(*args)

  def poll(self):
    at_landing_site = (self.current_room.room_id == 0x91F8)
    state = State.read_from(self.sock, self.rooms, self.doors,
        read_ship_state=at_landing_site)
    if state is None:
      return

    change = StateChange(self.prev_state, state, self.current_room)

    self.on_state_change(change)

    # When the room changes (and we're not in demo mode), we want to
    # take note.  Most of the time, the previous game state was
    # doorTransition, and we'll record the transition below.
    #
    # TODO: if we just started the room timer, or if we just loaded a
    # preset, then we won't know what the previous room was.  I think
    # that would require changes to the practice ROM.
    if change.is_room_change or change.reached_ship:
      self.handle_room_change(state, change)

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
        self.log("Ignoring transition from %s to %s (segment timer went backward from %s to %s)" % (
          self.last_room, state.room, self.prev_state.seg_rt, state.seg_rt))
      elif state.last_door_lag_frames == FrameCount(0):
        self.log("Transition not yet finished? (door time is 0.00)")
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
      self.log("Loading preset %04x; next transition may be wrong" % state.ram_load_preset)

    if change.is_playing and change.is_program_start and change.is_preset:
      self.log("Ignoring next transition due to starting in a room where a preset was loaded")
      self.ignore_next_transition = True

    elif change.is_playing and change.is_reset and change.is_preset:
      self.log("Ignoring next transition due to loading a preset")
      self.ignore_next_transition = True

    self.prev_state = state

  def handle_reset(self, state, change):
    # TODO: Can we differentiate between a reset due to failing the room
    # and a reset due to wanting to try the previous room again?

    if not self.ignore_next_transition:
      try:
        reset_id = TransitionId(self.last_room, self.last_most_recent_door,
            NullDoor, state.items, state.beams)
        self.on_reset(reset_id)
      except Exception as exc:
        self.log("Exception handing reset:")
        self.log("  state=%s" % state)
        self.log("  change=%s" % change)
        self.log("  exc=%s" % exc)

    # If we reset state to the middle of a door transition, then we
    # don't want to count the next transition, because it has already
    # been counted.
    if state.game_state == 'DoorTransition':
      self.ignore_next_transition = True

    if change.transition_finished:
      self.log("Reset detected during door transition")

    # TODO: I'm not sure if I want to do everything in
    # handle_room_change or just a subset
    self.current_room = NullRoom
    self.most_recent_door = NullDoor
    self.handle_room_change(state, change)

  def handle_room_change(self, state, change):
    if state.door.is_unknown:
      self.log("Unknown door %04x from %s (%04x) to %s (%04x)" % (
        state.door.door_id, self.current_room,
        self.current_room.room_id, state.room,
        state.room.room_id))
    self.last_room = self.current_room
    self.current_room = state.room
    self.last_most_recent_door = self.most_recent_door
    self.most_recent_door = state.door

  def handle_transition(self, state):
    if self.last_room is not self.last_most_recent_door.exit_room:
      self.log("Ignoring transition (entry door leads to %s, not %s)" %
          (self.last_most_recent_door.exit_room, self.last_room))
      return

    if self.last_room is not self.most_recent_door.entry_room:
      self.log("Ignoring transition (exit door is located in room %s, not %s)" %
          (self.most_recent_door.entry_room, self.last_room))
      return

    ts = datetime.datetime.now()
    try:
      transition_id = TransitionId(
          self.last_room, self.last_most_recent_door,
          self.most_recent_door, state.items, state.beams)
    except Exception as exc:
      self.log("Exception constructing transition id:")
      self.log("  state=%s" % state)
      self.log("  change=%s" % change)
      self.log("  exc=%s" % exc)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, state.last_door_lag_frames,
        state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    self.on_transitioned(transition)

  def handle_escaped_ceres(self, state):
    ts = datetime.datetime.now()
    transition_id = TransitionId(
        state.room, state.door, self.doors.from_id(0x88FE),
        state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, FrameCount(0), state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    self.on_transitioned(transition)

  def handle_reached_ship(self, state):
    ts = datetime.datetime.now()
    transition_id = TransitionId(
        state.room, state.door,
        NullDoor, state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_room_lag, FrameCount(0), state.last_realtime_door)
    transition = Transition(ts, transition_id, transition_time)
    self.on_transitioned(transition)

def color_for_time(ttime, atimes):
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

  return color

class RoomTimerTerminalFrontend(object):
  def __init__(self, debug_log=None, verbose=False):
    self.debug_log = debug_log
    self.verbose = verbose

  def log(self, *args):
    print(*args)

  def log_debug(self, *args):
    if self.debug_log:
      print(*args, file=self.debug_log)

  def log_verbose(self, *args):
    if self.verbose:
      self.log(*args)

  def state_changed(self, change):
    for s in change.description(): self.log_verbose(s)

  def new_room_time(self, transition, attempts, tracker):
    if self.verbose:
      # When verbose logging is enabled, we  want to minimize the number
      # of lines displayed
      # TODO: Colorize this the same as below
      self.log('%s #%s:' % (transition.id, len(attempts)))
    else:
      # Without verbose logging, we want to minimize the width of the
      # lines we are printing
      reset_id = TransitionId(transition.id.room, transition.id.entry_door,
          NullDoor, transition.id.items, transition.id.beams)
      resets = tracker.history.reset_count(reset_id)
      completions = tracker.history.completed_count(transition.id)
      denom = float(resets + completions)
      success_rate = int(float(completions) / denom * 100) if denom != 0 else 0
      self.log('Room: \033[1m%s\033[m (#%d, %d%% success)' %
          (transition.id.room, len(attempts), success_rate))
      self.log('Entered from: %s' % transition.id.entry_room)
      self.log('Exited to: %s' % transition.id.exit_room)

    self.log('Game: %s' % self.colorize(transition.time.gametime, attempts.gametimes))
    self.log('Real: %s' % self.colorize(transition.time.realtime, attempts.realtimes))
    self.log('Lag:  %s' % self.colorize(transition.time.roomlag, attempts.roomlagtimes))
    self.log('Door: %s' % self.colorize(transition.time.door, attempts.doortimes))
    # self.log('RD:   %s (%s)' % (transition.time.realtime_door, transition.time.realtime_door - transition.time.door))
    self.log('Tot:  %s' % (transition.time.totalrealtime))
    self.log('')

  def colorize(self, ttime, atimes):
    mean = atimes.mean()
    best = atimes.best()
    prev_best = atimes.prev_best()
    p50 = atimes.median()

    color = color_for_time(ttime, atimes)

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

  if args.debug_log_filename:
    debug_log = open(args.debug_log_filename, 'a')
    verbose = True
  elif args.debug:
    debug_log = sys.stdout
    verbose = True
  else:
    debug_log = None
    verbose = args.verbose

  frontend = RoomTimerTerminalFrontend(
      verbose=verbose, debug_log=debug_log)

  if args.filename is not None and os.path.exists(args.filename):
    history = read_transition_log(args.filename, rooms, doors)
  else:
    history = History()

  for tid in history:
    route.record(tid)
    if route.complete: break

  print('Route is %s' % ('complete' if route.complete else 'incomplete'))

  transition_log = FileTransitionLog(args.filename) if args.filename is not None else NullTransitionLog()

  if args.usb2snes:
    sock = WebsocketClient('sm_room_timer')
  else:
    sock = NetworkCommandSocket(logger=frontend)

  tracker = RoomTimeTracker(
      history, transition_log, route,
      on_new_room_time=frontend.new_room_time)

  timer = RoomTimer(
      frontend, rooms, doors, sock,
      on_transitioned=tracker.transitioned,
      on_state_change=frontend.state_changed,
      on_reset=tracker.room_reset)

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
