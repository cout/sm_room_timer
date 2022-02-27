#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file
from route import build_route, is_ceres_escape
from table import Cell, Table
from stats import transition_stats
from sm_segment_timer import Segment, find_segment_in_history

import sys
import argparse
import re

def find_transition_in_route(room, n, route):
  for tid in route:
    if tid.room == room:
      n -= 1
      if n <= 0:
        return tid

  raise RuntimeError("Could not find %s in route" % room_name)

def transition_from_name(name, rooms, route):
  if name == 'Alcatraz':
    name = 'Parlor 3'

  m = re.match('(.*?)\s+Revisited$', name)
  if m is not None:
    name = '%s 2' % m.group(1)

  m = re.match('(.*?)\s+(\d+)$', name)
  if m is None:
    room_name = name
    n = 1
  else:
    room_name = m.group(1)
    n = int(m.group(2))

  room = rooms.from_name(room_name)

  return find_transition_in_route(room, n, route)

def segment_from_name(name, rooms, route):
  start_transition_name, end_transition_name = name.split(' to ')
  start = transition_from_name(start_transition_name, rooms, route)
  end = transition_from_name(end_transition_name, rooms, route)
  return Segment(start, end)

def sum_of_best(segment, history, route):
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

def print_segment_stats(history, segment_history, segments):
  table = Table()

  underline = 4
  header = [ Cell(s, underline) for s in ( 'Segment', '%', '#', 'Median', 'Best', 'SOB', 'P50-P0', 'P50-SOB' ) ]
  table.append(header)

  total_p50 = FrameCount(0)
  total_p0 = FrameCount(0)
  total_sob = FrameCount(0)

  for segment in segments:
    attempts = find_segment_in_history(segment, history, route)
    segment_attempts = segment_history.get(tid, None)
    transitions = list(segment)
    if len(transitions) > 1:
      segment_attempt_count = len(segment_history[transitions[1]])
    else:
      segment_attempt_count = len(attempts)
    segment_success_count = len(attempts)
    rate = segment_success_count / segment_attempt_count

    p50 = attempts.totalrealtimes.median()
    p0 = attempts.totalrealtimes.best()
    sob = sum_of_best(segment, history, route)

    if any(( is_ceres_escape(tid) for tid in segment )):
      p50 += FrameCount(2591)
      p0 += FrameCount(2591)
      sob += FrameCount(2591)

    total_p50 += p50
    total_p0 += p0
    total_sob += sob

    table.append([
      Cell(segment),
      Cell(segment_success_count, justify='right'),
      Cell('%d%%' % (100 * rate), justify='right'),
      Cell(p50, justify='right'),
      Cell(p0, justify='right'),
      Cell(sob, justify='right'),
      Cell(p50 - p0, justify='right'),
      Cell(p50 - sob, justify='right'),
    ])

  table.append([
    Cell('Total'),
    Cell(''),
    Cell(''),
    Cell(total_p50, justify='right'),
    Cell(total_p0, justify='right'),
    Cell(total_sob, justify='right'),
    Cell(total_p50 - total_p0, justify='right'),
    Cell(total_p50 - total_sob, justify='right'),
  ])

  print(table.render())

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--segment', dest='segments', action='append', default=[])
  parser.add_argument('--split', dest='splits', action='append', default=[])
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  history = read_history_file(args.filename, rooms, doors)

  # ids = build_route(history) if args.build_route else history.keys()
  route = build_route(history) # TODO: Needed?

  segments = [ segment_from_name(name, rooms, route) for name in args.segments ]

  splits = [ transition_from_name(name, rooms, route) for name in args.splits ]
  start_split = False
  segment_start = route[0]
  for tid in route:
    if start_split:
      segment_start = tid
      start_split = False
    if tid in splits:
      segments.append(Segment(route, segment_start, tid))
      start_split = True

  segment_history = History()
  for segment in segments:
    attempts = find_segment_in_history(segment, history, route)
    for attempt in attempts:
      for transition in attempt:
        segment_history.record(transition)

  print_room_stats(history, segment_history, segments)
  print_segment_stats(history, segment_history, segments)
