#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file
from transition import Transition

import argparse
import csv

def print_table(table):
  width = { }
  for row in table:
    for idx, cell in enumerate(row):
      width[idx] = max(len(str(cell)), width.get(idx, 0))

  for row in table:
    print('  '.join([ str(cell).ljust(width[idx]) for idx, cell in enumerate(row) ]))

def build_route(filename):
  route = [ ]
  seen_transitions = { }
  next_room = None
  with open(args.filename) as infile:
    reader = csv.DictReader(infile)
    n = 1
    for row in reader:
      n += 1
      tid = Transition.from_csv_row(rooms, doors, row).id
      if (tid.entry_room is NullRoom or tid.exit_room is NullRoom) and tid.room is not LANDING_SITE and tid.room is not PARLOR:
        print("IGNORING (line %d): %s" % (n, tid))
        continue
      seen = seen_transitions.get(tid)
      if not seen:
        seen_transitions[tid] = True
        if next_room is None or t.room is next_room:
          route.append(tid)
        else:
          print("UNEXPECTED (line %d): %s" % (n, tid))
  return route

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--route', dest='build_route', action='store_true')
  parser.add_argument('--start', dest='start_room', default=None)
  parser.add_argument('--end', dest='end_room', default=None)
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  history = read_history_file(args.filename, rooms, doors)

  table = [ ]
  total_best = FrameCount(0)
  total_median = FrameCount(0)
  total_save = FrameCount(0)

  ids = build_route(args.filename) if args.build_route else history.keys()
  printing = False if args.start_room else True

  for id in ids:
    if args.start_room == id.room.name: printing = True
    if args.end_room == id.room.name: break
    if not printing: continue

    # TODO: We should keep stats for real+door, rather than keeping
    # those separately
    attempts = history[id]
    n = len(attempts.attempts)
    best = attempts.realtimes.best() + attempts.doortimes.best()
    median = attempts.realtimes.median() + attempts.doortimes.median()
    save = median - best
    total_best += best
    total_median += median
    total_save += save
    table.append([ id.room, n, best, median, save ]);

  table.append([ 'Total', '', total_best, total_median, total_save ]);
  print_table(table)
