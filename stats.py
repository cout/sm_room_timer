#!/usr/bin/env python3

from frame_count import FrameCount
from rooms import Room, Rooms, NullRoom
from doors import Doors, NullDoor
from history import History, read_history_file
from transition import Transition

from scipy import stats
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

def transition_stats(attempts):
  n = len(attempts.attempts)
  best = attempts.realtimes.best() + attempts.doortimes.best()
  p50 = attempts.realtimes.percentile(50) + attempts.doortimes.percentile(50)
  p75 = attempts.realtimes.percentile(75) + attempts.doortimes.percentile(75)
  p90 = attempts.realtimes.percentile(90) + attempts.doortimes.percentile(90)
  save = p50 - best
  return TransitionStats(room=id.room, n=n, best=best, p50=p50, p75=p75, p90=p90, save=save)

class Cell(object):
  def __init__(self, text, color=None):
    self.text = text
    self.color = color

  def __len__(self):
    return len(self.text)

  def __repr__(self):
    return repr(self.text)

  def __str__(self):
    return str(self.text)

  def __iter__(self):
    return iter(self.text)

  def width(self):
    return len(str(self.text))

  def render(self):
    return "\033[%sm%s\033[m" % ('' if self.color is None else self.color, self.text)

class Table(object):
  def __init__(self):
    self.rows = [ ]

  def append(self, row):
    self.rows.append(row)

  def __len__(self):
    return len(self.rows)

  def __iter__(self):
    return iter(self.rows)

  def render(self):
    width = { }
    for row in self.rows:
      for idx, cell in enumerate(row):
        width[idx] = max(cell.width(), width.get(idx, 0))

    lines = [ ]
    for row in self.rows:
      lines.append('  '.join([ cell.render() + ' '*(width[idx]-cell.width()) for idx, cell in enumerate(row) ]))

    return "\n".join(lines)

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
    all_stats.append(transition_stats(attempts))

  saves = [ s.save.count for s in all_stats ]
  p75_save = FrameCount(stats.scoreatpercentile(saves, 75))
  p90_save = FrameCount(stats.scoreatpercentile(saves, 90))
  print(p75_save)
  print(p90_save)

  table = Table()
  for s in all_stats:
    if s.save >= p90_save:
      color = '1;34'
    elif s.save >= p75_save:
      color = '1;33'
    else:
      color = None

    table.append([
      Cell(s.room, color),
      Cell(s.n, color),
      Cell(s.best, color),
      Cell(s.p50, color),
      Cell(s.p75, color),
      Cell(s.p90, color),
      Cell(s.save, color),
    ])

  total_best = FrameCount(sum([ s.best.count for s in all_stats ]))
  total_p50 = FrameCount(sum([ s.p50.count for s in all_stats ]))
  total_p75 = FrameCount(sum([ s.p75.count for s in all_stats ]))
  total_p90 = FrameCount(sum([ s.p90.count for s in all_stats ]))
  total_save = FrameCount(sum([ s.save.count for s in all_stats ]))
  table.append([ Cell('Total'), Cell(''), Cell(total_best),
    Cell(total_p50), Cell(total_p75), Cell(total_p90), Cell(total_save)
    ]);

  print(table.render())
