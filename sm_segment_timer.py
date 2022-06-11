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

  for segment_start_idx in history.indexes_by_tid.get(segment.start, []):
    attempt = SegmentAttempt()
    segment_iter = iter(segment)
    next_tid = next(segment_iter, None)

    for idx in range(segment_start_idx, len(history.all_transitions)):
      transition = history.all_transitions[idx]

      if next_tid is not None and transition.id == next_tid:
        # This is the next transition in the segment
        attempt.append(transition)
        next_tid = next(segment_iter, None)
        if transition.id == segment.end:
          attempts.append(attempt)

      else:
        # This is not the next transition in the segment (or the
        # previous transition was the end of the segment)
        break

  return attempts

@dataclass
class SegmentTransitionAttemptStats(object):
  """
  Statistics for a single transition in a segment attempt.
  """

  attempts: object
  num_attempts: int
  totalrealtime_p75: FrameCount
  totalrealtime_p50: FrameCount
  totalrealtime_p25: FrameCount
  totalrealtime_p0: FrameCount

  def __init__(self, transition, history):
    attempts = history.history.get(transition.id, None)

    if attempts is not None:
      self.attempts = attempts
      self.num_attempts = len(attempts)
      self.totalrealtime_p75 = attempts.totalrealtimes.percentile(75)
      self.totalrealtime_p50 = attempts.totalrealtimes.median()
      self.totalrealtime_p25 = attempts.totalrealtimes.percentile(25)
      self.totalrealtime_p0 = attempts.totalrealtimes.best()
    else:
      self.attempts = Attempts()
      self.num_attempts = 0
      self.totalrealtime_p75 = FrameCount(0)
      self.totalrealtime_p50 = FrameCount(0)
      self.totalrealtime_p25 = FrameCount(0)
      self.totalrealtime_p0 = FrameCount(0)

@dataclass
class SegmentAttemptStats(object):
  """
  Statistics for an entire segment attempt.
  """

  history: History
  transition_stats: list
  seg_attempts: list
  num_attempts: int
  totalrealtime_p75: FrameCount
  totalrealtime_p50: FrameCount
  totalrealtime_p25: FrameCount
  totalrealtime_p0: FrameCount

  def __init__(self, history):
    self.history = history
    self.transition_stats = [ ]
    self.seg_attempts = [ ]
    self.num_attempts = 0
    self.totalrealtime_p75 = None
    self.totalrealtime_p50 = None
    self.totalrealtime_p25 = None
    self.totalrealtime_p0 = None

  def append(self, transition, current_attempt):
    self.transition_stats.append(
        SegmentTransitionAttemptStats(transition, self.history))

    self.seg_attempts = find_segment_in_history(
        current_attempt.segment, self.history)

    historical_times = self.seg_attempts.totalrealtimes

    self.num_attempts = len(self.seg_attempts)
    self.totalrealtime_p75 = historical_times.percentile(75) if len(historical_times.values()) > 0 else FrameCount(0)
    self.totalrealtime_p50 = historical_times.median() if len(historical_times.values()) > 0 else FrameCount(0)
    self.totalrealtime_p25 = historical_times.percentile(25) if len(historical_times.values()) > 0 else FrameCount(0)
    self.totalrealtime_p0 = historical_times.best() if len(historical_times.values()) > 0 else FrameCount(0)

class SegmentTimeTracker(RoomTimeTracker):
  def __init__(self, history, transition_log, route,
      on_new_room_time=lambda *args, **kwargs: None,
      on_new_segment=lambda *args, **kwargs: None):
    RoomTimeTracker.__init__(
        self, history, transition_log, route,
        on_new_room_time=self.new_room_time)

    self.on_new_segment = on_new_segment
    self.on_new_room_in_segment_time = on_new_room_time

    self.current_attempt = SegmentAttempt()
    self.current_attempt_old_stats = None
    self.current_attempt_new_stats = None
    self.new_segment = True

  def transitioned(self, transition):

    if self.new_segment and (not self.route.complete or transition.id in self.route):
      self.on_new_segment(transition)
      self.current_attempt = SegmentAttempt()
      self.current_attempt_old_stats = SegmentAttemptStats(self.history)
      self.current_attempt_new_stats = SegmentAttemptStats(self.history)
      self.new_segment = False

    if self.current_attempt is not None and self.current_attempt_old_stats is not None:
      self.current_attempt.append(transition)
      self.current_attempt_old_stats.append(transition, self.current_attempt)
      print("updated old stats")

    RoomTimeTracker.transitioned(self, transition)

  def new_room_time(self, transition, attempts, tracker):
    # TODO: Tracking new/old stats like this means we do double the work
    # to find the segment in history
    if self.current_attempt is not None and self.current_attempt_new_stats is not None:
      self.current_attempt_new_stats.append(transition, self.current_attempt)
      print("updated new stats")

    self.on_new_room_in_segment_time(transition, attempts, tracker)

  def room_reset(self, reset_id):
    self.new_segment = True
    return RoomTimeTracker.room_reset(self, reset_id)

  def preset_loaded(self, state, change):
    self.new_segment = True
    return RoomTimeTracker.preset_loaded(self, state, change)

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

    transitions = self.tracker.current_attempt.transitions
    old_segment_stats = self.tracker.current_attempt_old_stats
    new_segment_stats = self.tracker.current_attempt_new_stats

    for transition, old_transition_stats, new_transition_stats in zip(transitions, old_segment_stats.transition_stats, new_segment_stats.transition_stats):
      time_color = color_for_time(
          transition.time.totalrealtime,
          old_transition_stats.attempts.totalrealtimes)

      time_color = '38;5;%s' % time_color
      cell_color = None

      room_p50_delta = transition.time.totalrealtime - old_transition_stats.totalrealtime_p50
      room_p0_delta = transition.time.totalrealtime - old_transition_stats.totalrealtime_p0

      table.append([
        Cell(transition.id.room, color=cell_color, max_width=28),
        Cell(new_transition_stats.num_attempts, color=cell_color, justify='right'),
        Cell(transition.time.totalrealtime, color=time_color, justify='right'),
        Cell(('+' if room_p50_delta > FrameCount(0) else '')
          + str(room_p50_delta), color=cell_color, justify='right'),
        Cell(('+' if room_p0_delta > FrameCount(0) else '')
          + str(room_p0_delta), color=cell_color, justify='right'),
      ])

    seg_time = self.tracker.current_attempt.time.totalrealtime
    seg_p50_delta = seg_time - old_segment_stats.totalrealtime_p50
    seg_p0_delta = seg_time - old_segment_stats.totalrealtime_p0

    color = color_for_time(
        self.tracker.current_attempt.time.totalrealtime,
        old_segment_stats.seg_attempts.totalrealtimes)
    table.append([
      Cell('Segment'),
      Cell(new_segment_stats.num_attempts, justify='right'),
      Cell(self.tracker.current_attempt.time.totalrealtime, '38;5;%s' % color, justify='right'),
      Cell(('+' if seg_p50_delta > FrameCount(0) else '') + str(seg_p50_delta), justify='right'),
      Cell(('+' if seg_p0_delta > FrameCount(0) else '') + str(seg_p0_delta), justify='right'),
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
        on_reset=tracker.room_reset,
        on_preset_loaded =self.tracker.preset_loaded)

    while state_reader.is_alive(): timer.poll()

  finally:
    state_reader.stop()

if __name__ == '__main__':
  main()
