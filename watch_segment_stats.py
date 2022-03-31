#!/usr/bin/env python3

from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_csv_incrementally
from route import build_route, is_ceres_escape
from segment_stats import SegmentStats, segment_from_name, transition_from_name, segments_from_splits
from table import Cell, Table

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

def render_change(old, new, **kwargs):
  if old > new:
    kwargs['color'] = '48;5;214'
  elif old < new:
    kwargs['color'] = '48;5;196'

  return Cell(new, **kwargs)

def print_segment_stats(old_stats, stats):
  table = Table()

  underline = 4
  header = [ Cell(s, underline) for s in ( 'Segment', '#', '%', 'Median', 'Best', 'SOB', 'P50-P0', 'P0-SOB' ) ]
  table.append(header)

  for old_seg, seg in zip(old_stats.segments, stats.segments):
    table.append([
      Cell(seg.segment.brief_name),
      Cell(seg.segment_success_count, justify='right'),
      Cell('%d%%' % (100 * seg.rate), justify='right'),
      render_change(old_seg.p50, seg.p50, justify='right'),
      render_change(old_seg.p0, seg.p0, justify='right'),
      render_change(old_seg.sob, seg.sob, justify='right'),
      render_change(old_seg.p50 - old_seg.p0, seg.p50 - seg.p0, justify='right'),
      render_change(old_seg.p0 - old_seg.sob, seg.p0 - seg.sob, justify='right'),
    ])

  table.append([
    Cell('Total'),
    Cell(''),
    Cell(''),
    render_change(old_stats.total_p50, stats.total_p50, justify='right'),
    render_change(old_stats.total_p0, stats.total_p0, justify='right'),
    render_change(old_stats.total_sob, stats.total_sob, justify='right'),
    render_change(old_stats.total_p50 - old_stats.total_p0, stats.total_p50 - stats.total_p0, justify='right'),
    render_change(old_stats.total_p0 - old_stats.total_sob, stats.total_p0 - stats.total_sob, justify='right'),
  ])

  print(table.render())

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--segment', dest='segments', action='append', default=[])
  parser.add_argument('--split', dest='splits', action='append', default=[])
  parser.add_argument('--splits', dest='splits_filename')
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

    old_stats = SegmentStats(history, segments)

    while True:
      stats = SegmentStats(history, segments)
      print_segment_stats(old_stats, stats)
      old_stats = stats
      history, transition = next(history_reader)
      print()

if __name__ == '__main__':
  main()
