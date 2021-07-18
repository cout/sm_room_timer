#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file
from transition import Transition

from typing import NamedTuple
import argparse
import csv

class TransitionStats(NamedTuple):
  room: str
  n: int
  best: FrameCount
  p50: FrameCount
  p75: FrameCount
  p90: FrameCount
  save: FrameCount

def stats(attempts):
  n = len(attempts.attempts)
  best = attempts.realtimes.best() + attempts.doortimes.best()
  p50 = attempts.realtimes.percentile(50) + attempts.doortimes.percentile(50)
  p75 = attempts.realtimes.percentile(75) + attempts.doortimes.percentile(75)
  p90 = attempts.realtimes.percentile(90) + attempts.doortimes.percentile(90)
  save = p50 - best
  return TransitionStats(room=id.room, n=n, best=best, p50=p50, p75=p75, p90=p90, save=save)

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

  ids = build_route(args.filename) if args.build_route else history.keys()
  printing = False if args.start_room else True

  all_stats = [ ]
  for id in ids:
    if args.start_room == id.room.name: printing = True
    if args.end_room == id.room.name: break
    if not printing: continue

    # TODO: We should keep stats for real+door, rather than keeping
    # those separately
    attempts = history[id]
    all_stats.append(stats(attempts))

  table = [ ]
  for s in all_stats:
    table.append([ s.room, s.n, s.best, s.p50, s.p75, s.p90, s.save ])

  total_best = FrameCount(sum([ s.best.count for s in all_stats ]))
  total_p50 = FrameCount(sum([ s.p50.count for s in all_stats ]))
  total_p75 = FrameCount(sum([ s.p75.count for s in all_stats ]))
  total_p90 = FrameCount(sum([ s.p90.count for s in all_stats ]))
  total_save = FrameCount(sum([ s.save.count for s in all_stats ]))
  table.append([ 'Total', '', total_best, total_p50, total_p75, total_p90, total_save ]);

  print_table(table)
