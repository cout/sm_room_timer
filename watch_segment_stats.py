#!/usr/bin/env python3

from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_csv_incrementally
from route import build_route, is_ceres_escape
from sm_segment_timer import Segment, find_segment_in_history
from segment_stats import print_room_stats, print_segment_stats, \
segment_from_name, transition_from_name, segments_from_splits, \
build_segment_history

import sys
import argparse
import re
import time

class Tailer(object):
  def __init__(self, f, t=0.1):
    self._f = f
    self._t = t
    self._buf = ''
    self._line = None

    self.step()

  def step(self):
    self._line = None
    s = self._f.readline()
    if s is not None:
      self._buf += s
      if self._buf.endswith("\n"):
        self._line = self._buf
        self._buf = ''

  def at_eof(self):
    return self._line is None

  def __iter__(self):
    return self

  def __next__(self):
    while True:
      line = self._line
      self.step()
      if line is not None:
        return line
      time.sleep(self._t)

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

  with open(args.filename) as csvfile:
    tailer = Tailer(csvfile)
    history_reader = read_history_csv_incrementally(tailer, rooms, doors)

    while not tailer.at_eof():
      history, transition = next(history_reader)

    # ids = build_route(history) if args.build_route else history.keys()
    route = build_route(history) # TODO: Needed?

    split_names = args.splits

    if args.splits_filename is not None:
      with open(args.splits_filename) as f:
        lines = [ line for line in f.readlines()
            if not line.startswith('#') and not line.isspace() ]
        split_names.extend([ line.strip() for line in lines ])

    segments = [ segment_from_name(name, rooms, route) for name in args.segments ]
    splits = [ transition_from_name(name, rooms, route) for name in split_names ]

    segments.extend(segments_from_splits(route, splits))

    while True:
      print_segment_stats(history, segments)
      history, transition = next(history_reader)
      print()

if __name__ == '__main__':
  main()
