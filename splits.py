from segment import Segment

import re

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

  return route.find_nth_transition_by_room(room, n)

def segment_from_name(name, rooms, route):
  start_transition_name, end_transition_name = name.split(' to ')
  start = transition_from_name(start_transition_name, rooms, route)
  end = transition_from_name(end_transition_name, rooms, route)
  return Segment.from_route(route, start, end)

def segments_from_splits(route, splits):
  segments = [ ]
  if len(route) > 0:
    start_split = False
    segment_start = route[0]
    for tid in route:
      if start_split:
        segment_start = tid
        start_split = False
      if tid in splits:
        segments.append(Segment.from_route(route, segment_start, tid))
        start_split = True
  return segments

def read_split_names_from_file(filename):
  with open(filename) as f:
    lines = [ line for line in f.readlines()
        if not line.startswith('#') and not line.isspace() ]
    return [ line.strip() for line in lines ]

class Splits(list):
  @classmethod
  def from_segment_and_split_names(cls, segment_names, split_names,
      rooms, route):
    segments = [ segment_from_name(name, rooms, route) for name in segment_names ]
    splits = [ transition_from_name(name, rooms, route) for name in split_names ]

    segments.extend(segments_from_splits(route, splits))

    return segments
