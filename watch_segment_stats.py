#!/usr/bin/env python3

from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History
from transition_log import read_transition_log_csv_incrementally
from route import build_route, is_ceres_escape
from segment_stats import SegmentStats
from splits import Splits
from table import Cell, Table, CompactRenderer
from frame_count import FrameCount

import sys
import argparse
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
  if new < old:
    kwargs['color'] = '48;5;34;1'
  elif new > old:
    kwargs['color'] = '48;5;124;1'

  return Cell(new, **kwargs)

def render_delta_to_best(old_best, new_best, delta, **kwargs):
  if new_best < old_best:
    kwargs['color'] = '38;5;214;7'

  pos = '+' if delta > FrameCount(0) else ''
  return Cell(pos + str(delta), **kwargs)

def render_segment_stats(old_stats, stats):
  table = Table(renderer=CompactRenderer())

  underline = 4
  header = [ Cell(s, underline) for s in ( 'Segment', '#', '%', 'Median', '±Best', '±SOB' ) ]
  table.append(header)

  for old_seg, seg in zip(old_stats.segments, stats.segments):
    table.append([
      Cell(seg.segment.brief_name),
      Cell(seg.segment_success_count, justify='right'),
      Cell('%d%%' % (100 * seg.rate), justify='right'),
      render_change(old_seg.p50, seg.p50, justify='right'),
      render_delta_to_best(old_seg.p0, seg.p0, seg.p50 - seg.p0, justify='right'),
      render_delta_to_best(old_seg.sob, seg.sob, seg.p50 - seg.sob, justify='right'),
    ])

  table.append([
    Cell('Total'),
    Cell(''),
    Cell(''),
    render_change(old_stats.total_p50, stats.total_p50, justify='right'),
    render_delta_to_best(old_stats.total_p0, stats.total_p0, stats.total_p50 - stats.total_p0, justify='right'),
    render_delta_to_best(old_stats.total_sob, stats.total_sob, stats.total_p50 - stats.total_sob, justify='right'),
  ])

  table.append([
    Cell(''),
    Cell(''),
    Cell(''),
    Cell(''),
    Cell('%s' % stats.total_p0, justify='right'),
    Cell('%s' % stats.total_sob, justify='right'),
  ])

  return table.render()

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
    history_reader = read_transition_log_csv_incrementally(tailer, rooms, doors)

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

    segments = Splits.from_segment_and_split_names(
        args.segments,
        split_names,
        rooms,
        route)

    old_stats = SegmentStats(history, segments)
    old_rendered_stats = None

    while True:
      stats = SegmentStats(history, segments)
      rendered_stats = render_segment_stats(old_stats, stats)
      if rendered_stats != old_rendered_stats:
        print()
        print()
        print(rendered_stats, end='', flush=True)
        old_rendered_stats = rendered_stats
      old_stats = stats
      history, transition = next(history_reader)

if __name__ == '__main__':
  main()
