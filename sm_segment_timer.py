#!/usr/bin/env python3

from sm_room_timer import Store, RoomTimer, TerminalFrontend, backup_and_rebuild
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from route import Route
from frame_count import FrameCount
from transition import TransitionTime
from history import Attempts, History
from table import Cell, Table
from rebuild_history import need_rebuild, rebuild_history
from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient

import argparse
import itertools
import time
import sys

class Segment(object):
  def __init__(self, tids=None):
    self.tids = tids or []

  @classmethod
  def from_route(cls, route, start=None, end=None):
    in_segment = False
    tids = [ ]
    for tid in route:
      if tid == start: in_segment = True
      if in_segment: tids.append(tid)
      if tid == end: break
    return Segment(tids)

  @property
  def start(self):
    return self.tids[0]

  @property
  def end(self):
    return self.tids[-1]

  def __str__(self):
    return "%s to %s" % (self.start.room, self.end.room)

  def __repr__(self):
    return "Segment(%s)" % (self.tids)

  def __iter__(self):
    return iter(self.tids)

  def extend_to(self, tid):
    self.tids.append(tid)

class SegmentTime(TransitionTime):
  pass

class SegmentAttempt(object):
  def __init__(self, transitions=None):
    self.segment = Segment()
    self.transitions = transitions or [ ]
    self.time = SegmentTime(
        gametime=FrameCount(0),
        realtime=FrameCount(0),
        roomlag=FrameCount(0),
        door=FrameCount(0),
        realtime_door=FrameCount(0))

  def __repr__(self):
    return 'SegmentAttempt(%s)' % repr(self.transitions)

  def __len__(self):
    return len(self.transitions)

  def __iter__(self):
    return iter(self.transitions)

  def append(self, transition):
    self.segment.extend_to(transition.id)
    self.transitions.append(transition)
    self.time += transition.time

class SegmentAttempts(Attempts):
  def __init__(self, transitions=None):
    Attempts.__init__(self, transitions)

  def __repr__(self):
    return 'SegmentAttempts(%s)' % repr(self.attempts)

def find_segment_in_history(segment, history):
  attempts = SegmentAttempts()
  attempt = None
  segment_iter = None
  next_tid = None

  for transition in history.all_transitions:
    if transition.id == segment.start:
      # This is the start
      attempt = SegmentAttempt()
      segment_iter = iter(segment)
      next_tid = next(segment_iter, None)

    if next_tid is not None and transition.id == next_tid:
      # This is the next transition in the segment
      attempt.append(transition)
      next_tid = next(segment_iter, None)
      if transition.id == segment.end:
        attempts.append(attempt)

    else:
      # This is not the next transition in the segment (or the
      # previous transtition was the end of the segment)
      attempt = None
      segment_iter = None
      next_tid = None

  return attempts

class SegmentTransitionAttemptStats(object):
  def __init__(self, transition, history):
    self.attempts = history.history[transition.id]
    self.transition = transition
    self.num_attempts = len(self.attempts)
    self.p50_delta = transition.time.totalrealtime - self.attempts.totalrealtimes.median()
    self.p0_delta = transition.time.totalrealtime - self.attempts.totalrealtimes.best()

class SegmentAttemptStats(object):
  def __init__(self, history, route):
    self.history = history
    self.route = route

    self.p50_deltas = [ ]
    self.max_p50_delta = None
    self.min_p50_delta = None

    self.p0_deltas = [ ]
    self.max_p0_delta = None
    self.min_p0_delta = None

    self.transitions = [ ]
    self.seg_attempts = [ ]

  def append(self, transition, current_attempt):
    self.p50_deltas.append(transition.time.totalrealtime -
        self.history.history[transition.id].totalrealtimes.median())
    self.max_p50_delta = max(self.p50_deltas)
    self.min_p50_delta = min(self.p50_deltas)

    self.p0_deltas.append(transition.time.totalrealtime -
        self.history.history[transition.id].totalrealtimes.median())
    self.max_p0_delta = max(self.p0_deltas)
    self.min_p0_delta = min(self.p0_deltas)

    self.transitions.append(
        SegmentTransitionAttemptStats(transition, self.history))

    self.seg_attempts = find_segment_in_history(
        current_attempt.segment, self.history)
    self.num_attempts = len(self.seg_attempts)
    self.p50_delta = current_attempt.time.totalrealtime - self.seg_attempts.totalrealtimes.median();
    self.p0_delta = current_attempt.time.totalrealtime - self.seg_attempts.totalrealtimes.best();

class SegmentStore(Store):
  def __init__(self, rooms, doors, route, filename=None):
    Store.__init__(self, rooms, doors, route, filename=filename)

    self.current_attempt = SegmentAttempt()
    self.current_attempt_stats = None
    self.route_iter = None

  def transitioned(self, transition):
    # TODO: Do we really want to check if the transition is in the route
    # when not using --route?
    if self.route_iter is None:
      next_tid = None
      new_segment = True
    else:
      next_tid = next(self.route_iter, None)
      new_segment = next_tid is None or next_tid != transition.id

    if new_segment:
      # This is the first transition in a segment; let's see if we can
      # find the segment in the route.
      self.route_iter = itertools.dropwhile(
          lambda tid: transition.id != tid,
          self.route)
      next_tid = next(self.route_iter, None)

      if next_tid is not None:
        # If this transition is in the route, start a new segment.
        print("New segment starting at %s" % transition.id)
        self.current_attempt = SegmentAttempt()
        self.current_attempt_stats = SegmentAttemptStats(self.history,
            self.route)

      else:
        # If this transition is not in the route, ignore it (base class
        # will display a message to the user).
        self.current_attempt = None
        self.current_attempt_stats = None

    if self.current_attempt is not None and self.current_attempt_stats is not None:
      self.current_attempt.append(transition)
      self.current_attempt_stats.append(transition, self.current_attempt)

    attempts = Store.transitioned(self, transition)

    return attempts

class SegmentTimer(RoomTimer):
  def __init__(self, rooms, doors, store, sock, debug_log=None, verbose=False):
    RoomTimer.__init__(self, rooms, doors, store, sock, debug_log, verbose)

class SegmentTimerTerminalFrontend(TerminalFrontend):
  def __init__(self, debug_log=None, verbose=False):
    TerminalFrontend.__init__(self, debug_log=debug_log, verbose=verbose)

  def log_transition(self, transition, attempts, store):
    print("Segment: \033[1m%s\033[m" % store.current_attempt.segment)

    table = Table()

    underline = 4
    header = [ Cell(s, underline) for s in ( 'Room', '#', 'Time', '±Median', '±Best' ) ]
    table.append(header)

    # stats = SegmentAttemptStats(store.current_attempt, store.history,
        # store.route)

    # stats = SegmentAttemptStats(store.history, store.route)
    # for transition in store.current_attempt:
      # stats.append(transition, store.current_attempt)
    stats = store.current_attempt_stats

    for transition_stats in stats.transitions:
      transition = transition_stats.transition

      time_color = self.color_for_time(
          transition.time.totalrealtime,
          transition_stats.attempts.totalrealtimes)

      if transition_stats.p50_delta == stats.max_p50_delta:
        # time_color = '1;48;5;65;38;5;%s' % time_color
        # cell_color = '48;5;65'
        time_color = '38;5;%s' % time_color
        cell_color = None
      elif transition_stats.p50_delta == stats.min_p50_delta:
        # time_color = '1;48;5;95;38;5;%s' % time_color
        # cell_color = '48;5;95'
        time_color = '38;5;%s' % time_color
        cell_color = None
      else:
        time_color = '38;5;%s' % time_color
        cell_color = None

      table.append([
        Cell(transition.id.room, color=cell_color, max_width=28),
        Cell(transition_stats.num_attempts, color=cell_color, justify='right'),
        Cell(transition.time.totalrealtime, color=time_color, justify='right'),
        Cell(('+' if transition_stats.p50_delta > FrameCount(0) else '')
          + str(transition_stats.p50_delta), color=cell_color, justify='right'),
        Cell(('+' if transition_stats.p0_delta > FrameCount(0) else '')
          + str(transition_stats.p0_delta), color=cell_color, justify='right'),
      ])

    color = self.color_for_time(
        store.current_attempt.time.totalrealtime,
        stats.seg_attempts.totalrealtimes)
    table.append([
      Cell('Segment'),
      Cell(stats.num_attempts, justify='right'),
      Cell(store.current_attempt.time.totalrealtime, '38;5;%s' % color, justify='right'),
      Cell(('+' if stats.p50_delta > FrameCount(0) else '') + str(stats.p50_delta), justify='right'),
      Cell(('+' if stats.p0_delta > FrameCount(0) else '') + str(stats.p0_delta), justify='right'),
    ])

    print(table.render())
    print('')

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
  # parser.add_argument('--segment', action='append', required=True)
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

  store = SegmentStore(rooms, doors, route, args.filename)
  frontend = SegmentTimerTerminalFrontend(verbose=verbose, debug_log=debug_log)

  if args.usb2snes:
    sock = WebsocketClient('sm_room_timer', logger=frontend)
  else:
    sock = NetworkCommandSocket()

  timer = SegmentTimer(frontend, rooms, doors, store, sock)

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
