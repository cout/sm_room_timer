#!/usr/bin/env python3

from sm_room_timer import RoomTimeTracker, RoomTimer, ThreadedStateReader, backup_and_rebuild, color_for_time
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from route import Route, DummyRoute
from frame_count import FrameCount
from transition import TransitionTime
from transition_log import read_transition_log, FileTransitionLog, NullTransitionLog
from history import Attempts, History
from segment import Segment
from table import Cell, Table
from rebuild_history import need_rebuild, rebuild_history

from dataclasses import dataclass
import argparse
import itertools
import time
import sys
import os

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
        realtime_door=FrameCount(0),
        doortime_is_real=True)

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

@dataclass
class SegmentTransitionAttemptStats(object):
  """
  Statistics for a single transition in a segment attempt.
  """

  attempts: object
  num_attempts: int
  time: FrameCount
  p50: FrameCount
  p0: FrameCount
  p50_delta: FrameCount
  p0_delta: FrameCount

  def __init__(self, transition, history):
    self.transition = transition
    self.time = transition.time.totalrealtime

    attempts = history.history.get(transition.id, None)

    if attempts is not None:
      self.attempts = attempts
      self.num_attempts = len(attempts)
      self.p50 = attempts.totalrealtimes.median()
      self.p0 = attempts.totalrealtimes.best()
      self.p50_delta = self.time - self.p50
      self.p0_delta = self.time - self.p0
    else:
      self.attempts = Attempts()
      self.num_attempts = 0
      self.p50 = FrameCount(0)
      self.p0 = FrameCount(0)
      self.p50_delta = FrameCount(0)
      self.p0_delta = FrameCount(0)

@dataclass
class SegmentAttemptStats(object):
  """
  Statistics for an entire segment attempt.
  """

  history: History
  transitions: list
  seg_attempts: list

  def __init__(self, history):
    self.history = history
    self.transitions = [ ]
    self.seg_attempts = [ ]

  def append(self, transition, current_attempt):
    self.transitions.append(
        SegmentTransitionAttemptStats(transition, self.history))

    self.seg_attempts = find_segment_in_history(
        current_attempt.segment, self.history)

    attempt_time = current_attempt.time.totalrealtime
    historical_times = self.seg_attempts.totalrealtimes

    self.num_attempts = len(self.seg_attempts)
    self.p50 = historical_times.median() if len(historical_times.values()) > 0 else FrameCount(0)
    self.p0 = historical_times.best() if len(historical_times.values()) > 0 else FrameCount(0)
    self.p50_delta = attempt_time - self.p50
    self.p0_delta = attempt_time - self.p0

class SegmentTimeTracker(RoomTimeTracker):
  def __init__(self, history, transition_log, route,
      on_new_room_time=lambda *args, **kwargs: None,
      on_new_segment=lambda *args, **kwargs: None):
    RoomTimeTracker.__init__(
        self, history, transition_log, route,
        on_new_room_time=on_new_room_time)

    self.on_new_segment = on_new_segment

    self.current_attempt = SegmentAttempt()
    self.current_attempt_stats = None
    self.new_segment = True

  def transitioned(self, transition):

    if self.new_segment and (not self.route.complete or transition.id in self.route):
      self.on_new_segment(transition)
      self.current_attempt = SegmentAttempt()
      self.current_attempt_stats = SegmentAttemptStats(self.history)
      self.new_segment = False

    if self.current_attempt is not None and self.current_attempt_stats is not None:
      self.current_attempt.append(transition)
      self.current_attempt_stats.append(transition, self.current_attempt)

    RoomTimeTracker.transitioned(self, transition)

  def room_reset(self, reset_id):
    self.new_segment = True
    return RoomTimeTracker.room_reset(self, reset_id)

class SegmentTimer(RoomTimer):
  pass

class SegmentTimeTable(object):
  def __init__(self, attempts, tracker):
    self.attempts = attempts
    self.tracker = tracker

  def render(self):
    table = Table()

    underline = 4
    header = [ Cell(s, underline) for s in ( 'Room', '#', 'Time', '±Median', '±Best' ) ]
    table.append(header)

    stats = self.tracker.current_attempt_stats

    for transition_stats in stats.transitions:
      transition = transition_stats.transition

      time_color = color_for_time(
          transition.time.totalrealtime,
          transition_stats.attempts.totalrealtimes)

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

    color = color_for_time(
        self.tracker.current_attempt.time.totalrealtime,
        stats.seg_attempts.totalrealtimes)
    table.append([
      Cell('Segment'),
      Cell(stats.num_attempts, justify='right'),
      Cell(self.tracker.current_attempt.time.totalrealtime, '38;5;%s' % color, justify='right'),
      Cell(('+' if stats.p50_delta > FrameCount(0) else '') + str(stats.p50_delta), justify='right'),
      Cell(('+' if stats.p0_delta > FrameCount(0) else '') + str(stats.p0_delta), justify='right'),
    ])

    return table.render()

class SegmentTimerTerminalFrontend(object):
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
    print("Segment: \033[1m%s\033[m" % tracker.current_attempt.segment)

    table = SegmentTimeTable(attempts, tracker)

    print(table.render())
    print('')

    # old_median = self.tracker.current_attempt_stats.p50
    # new_median = find_segment_in_history(
    #     self.tracker.current_attempt.segment,
    #     self.tracker.history).totalrealtimes.median()
    # self.log_verbose('Old median:', old_median)
    # self.log_verbose('New median:', new_median)

    # if new_median < old_median:
     #  print("You lowered your median time by %s!" % (new_median - old_median))

  def new_segment(self, transition):
    print("New segment starting at %s" % transition.id)

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

  frontend = SegmentTimerTerminalFrontend(
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

  tracker = SegmentTimeTracker(
      history, transition_log, route,
      on_new_room_time=frontend.new_room_time)

  state_reader = ThreadedStateReader(
      rooms, doors,
      usb2snes=args.usb2snes, logger=frontend)
  state_reader.start()

  try:
    timer = SegmentTimer(
        frontend, state_reader,
        on_transitioned=tracker.transitioned,
        on_state_change=frontend.state_changed,
        on_reset=tracker.room_reset)

    while state_reader.is_alive(): timer.poll()

  finally:
    state_reader.stop()

if __name__ == '__main__':
  main()
