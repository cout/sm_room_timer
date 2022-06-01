#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History
from transition_log import read_transition_log
from route import build_route, is_ceres_escape
from table import Cell, Table
from stats import transition_stats
from splits import Splits, read_split_names_from_file
from sm_segment_timer import find_segment_in_history

import sys
import argparse

def sum_of_best(segment, history):
  total = FrameCount(0)
  for tid in segment:
    total += history[tid].totalrealtimes.best()
  return total

def print_room_stats(history, segment_history, segments):
  for segment in segments:
    print("Segment: \033[1m%s\033[m" % segment)

    table = Table()

    underline = 4
    header = [ Cell(s, underline) for s in ( 'Room', '#', '%', 'Median',
      'Best', 'Seg Median', 'Seg Best', 'Delta Median', 'Delta Best' ) ]
    table.append(header)

    total_p50 = FrameCount(0)
    total_p0 = FrameCount(0)
    total_p50_seg = FrameCount(0)
    total_p0_seg = FrameCount(0)

    for idx, tid in enumerate(segment):
      if not tid in segment_history:
        print("BUG? Could not find any attempts for %s in segment %s" % (tid, segment))
        continue

      if idx <= 1: segment_attempt_count = len(segment_history[tid])
      room_attempt_count = len(segment_history[tid])
      rate = room_attempt_count / segment_attempt_count

      p50 = history[tid].totalrealtimes.median()
      p0 = history[tid].totalrealtimes.best()
      seg_p50 = segment_history[tid].totalrealtimes.median()
      seg_p0 = segment_history[tid].totalrealtimes.best()

      total_p50 += p50
      total_p0 += p0
      total_p50_seg += seg_p50
      total_p0_seg += seg_p0

      table.append([
        Cell(tid.room.name),
        Cell(len(segment_history[tid]), justify='right'),
        Cell('%d%%' % (100 * rate), justify='right'),
        Cell(p50, justify='right'),
        Cell(p0, justify='right'),
        Cell(seg_p50, justify='right'),
        Cell(seg_p0, justify='right'),
        Cell(seg_p50 - p50, justify='right'),
        Cell(seg_p0 - p0, justify='right'),
      ])

    table.append([
      Cell('Total'),
      Cell('', justify='right'),
      Cell(''),
      Cell(total_p50, justify='right'),
      Cell(total_p0, justify='right'),
      Cell(total_p50_seg, justify='right'),
      Cell(total_p0_seg, justify='right'),
      Cell(total_p50_seg - total_p50, justify='right'),
      Cell(total_p0_seg - total_p0, justify='right'),
    ])

    print(table.render())
    print('')

class SingleSegmentStats(object):
  def __init__(self, segment, history):
    self.segment = segment

    successful_attempts = find_segment_in_history(segment, history)
    # The number of segment attempts is the number of times we attempted
    # the first three rooms in the segment in succession.
    all_attempts = find_segment_in_history(segment[0:2], history)
    self.segment_attempt_count = len(all_attempts)

    self.segment_success_count = len(successful_attempts)
    self.rate = self.segment_success_count / self.segment_attempt_count if self.segment_attempt_count > 0 else 0

    self.p50 = successful_attempts.totalrealtimes.median()
    self.p0 = successful_attempts.totalrealtimes.best()
    self.sob = sum_of_best(segment, history)

    if any(( is_ceres_escape(tid) for tid in segment )):
      self.p50 += FrameCount(2591)
      self.p0 += FrameCount(2591)
      self.sob += FrameCount(2591)

class SegmentStats(object):
  def __init__(self, history, segments):
    self.segments = [ ]
    self.total_p50 = FrameCount(0)
    self.total_p0 = FrameCount(0)
    self.total_sob = FrameCount(0)

    for segment in segments:
      stats = SingleSegmentStats(segment, history)
      self.segments.append(stats)

      self.total_p50 += stats.p50
      self.total_p0 += stats.p0
      self.total_sob += stats.sob

def print_segment_stats(history, segments):
  stats = SegmentStats(history, segments)

  table = Table()

  underline = 4
  header = [ Cell(s, underline) for s in ( 'Segment', '#', '%', 'Median', 'Best', 'SOB', 'P50-P0', 'P0-SOB' ) ]
  table.append(header)

  for seg in stats.segments:
    table.append([
      Cell(seg.segment),
      Cell(seg.segment_success_count, justify='right'),
      Cell('%d%%' % (100 * seg.rate), justify='right'),
      Cell(seg.p50, justify='right'),
      Cell(seg.p0, justify='right'),
      Cell(seg.sob, justify='right'),
      Cell(seg.p50 - seg.p0, justify='right'),
      Cell(seg.p0 - seg.sob, justify='right'),
    ])

  table.append([
    Cell('Total'),
    Cell(''),
    Cell(''),
    Cell(stats.total_p50, justify='right'),
    Cell(stats.total_p0, justify='right'),
    Cell(stats.total_sob, justify='right'),
    Cell(stats.total_p50 - stats.total_p0, justify='right'),
    Cell(stats.total_p0 - stats.total_sob, justify='right'),
  ])

  print(table.render())

def build_segment_history(segments, history):
  segment_history = History()
  for segment in segments:
    attempts = find_segment_in_history(segment, history)
    for attempt in attempts:
      for transition in attempt:
        segment_history.record(transition)
  return segment_history

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--segment', dest='segments', action='append', default=[])
  parser.add_argument('--split', dest='splits', action='append', default=[])
  parser.add_argument('--splits', dest='splits_filename')
  parser.add_argument('--brief', action='store_true')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  history = read_transition_log(args.filename, rooms, doors)

  # ids = build_route(history) if args.build_route else history.keys()
  route = build_route(history) # TODO: Needed?

  split_names = args.splits

  if args.splits_filename is not None:
    split_names.extend(read_split_names_from_file(args.splits_filename))

  segments = Splits.from_segment_and_split_names(
      args.segments,
      split_names,
      rooms,
      route)

  if not args.brief:
    segment_history = build_segment_history(segments, history)
    print_room_stats(history, segment_history, segments)
  print_segment_stats(history, segments)

if __name__ == '__main__':
  main()
