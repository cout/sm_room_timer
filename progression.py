#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file, read_history_file_incrementally
from route import Route, build_route, is_ceres_escape
from transition import Transition
from stats import TransitionStats, transition_stats, ceres_cutscene_stats, door_stats

from scipy import stats
import argparse
import csv

def progression_stats(filename, route, rooms, doors, start_room=None, end_room=None):
  printing = False if start_room else True

  all_stats = { }
  route = Route()

  for history, transition in read_history_file_incrementally(args.filename, rooms, doors):
    tid = transition.id
    route.record(tid, verbose=False)

    if tid in route:
      if start_room == tid.room.name: printing = True
      if end_room == tid.room.name: break
      if not printing: continue

      attempts = history[tid]

      all_stats[tid] = transition_stats(tid, attempts, iqr=True,
        exclude_doors=args.exclude_doors, doors_only=args.doors_only)

      if is_ceres_escape(tid) and not args.doors_only:
        all_stats['ceres cutscene'] = ceres_cutscene_stats(tid, attempts, iqr=True)

      yield transition, all_stats

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Graph Progression')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--start', dest='start_room', default=None)
  parser.add_argument('--end', dest='end_room', default=None)
  parser.add_argument('--exclude-doors', action='store_true')
  parser.add_argument('--doors-only', action='store_true')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)

  history = read_history_file(args.filename, rooms, doors)
  route = Route()
  ids = build_route(history)
  all_stats = { }

  print('Timestamp,Room,Route Sum of Best,Route Sum of P25,Route Sum of P50,Route Sum of P75,Route Sum of P90')

  for transition, all_stats in progression_stats(args.filename, route,
      rooms, doors, start_room=args.start_room, end_room=args.end_room):

    p0 = FrameCount(sum([ s.best.count for s in all_stats.values() ]))
    p25 = FrameCount(sum([ s.p25.count for s in all_stats.values() ]))
    p50 = FrameCount(sum([ s.p50.count for s in all_stats.values() ]))
    p75 = FrameCount(sum([ s.p75.count for s in all_stats.values() ]))
    p90 = FrameCount(sum([ s.p90.count for s in all_stats.values() ]))

    print('%s,%s,%s,%s,%s,%s,%s' % (
      transition.ts,
      transition.id.room,
      round(p0.to_seconds(), 3),
      round(p25.to_seconds(), 3),
      round(p50.to_seconds(), 3),
      round(p75.to_seconds(), 3),
      round(p90.to_seconds(), 3)))
