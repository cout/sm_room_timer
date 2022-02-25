#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file
from route import build_route, is_ceres_escape
from table import Cell, Table
from stats import transition_stats, ceres_cutscene_stats, door_stats
from sm_segment_timer import Segment, SegmentTime, SegmentAttempt, SegmentAttempts, find_segment_in_history

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

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--segment', dest='segments', action='append')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  history = read_history_file(args.filename, rooms, doors)

  # ids = build_route(history) if args.build_route else history.keys()
  route = build_route(history) # TODO: Needed?

  table = Table()

  underline = 4
  header = [ Cell(s, underline) for s in ( 'Segment', '#', 'Median', 'Best', 'P50-P0' ) ]
  table.append(header)

  segments = [ segment_from_name(name, rooms, route) for name in args.segments ]

  total_p50 = FrameCount(0)
  total_p0 = FrameCount(0)

  for segment in segments:
    attempts = find_segment_in_history(segment, history, route)

    p50 = attempts.totalrealtimes.median()
    p0 = attempts.totalrealtimes.best()

    total_p50 += p50
    total_p0 += p0

    table.append([
      Cell(segment),
      Cell(len(attempts), justify='right'),
      Cell(p50, justify='right'),
      Cell(p0, justify='right'),
      Cell(p50 - p0, justify='right'),
    ])

  table.append([
    Cell('Total'),
    Cell('', justify='right'),
    Cell(total_p50, justify='right'),
    Cell(total_p0, justify='right'),
    Cell(total_p50 - total_p0, justify='right'),
  ])

  print(table.render())
