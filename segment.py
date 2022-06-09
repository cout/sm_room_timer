from transition import TransitionId

from dataclasses import dataclass

@dataclass
class Segment(object):
  tids: list
  start: TransitionId
  end: TransitionId

  def __init__(self, tids=None):
    tids = tids or [ ]
    self.tids = tids
    self.start = tids[0] if len(tids) > 0 else None
    self.end = tids[-1] if len(tids) > 0 else None

  @classmethod
  def from_route(cls, route, start=None, end=None):
    in_segment = False
    tids = [ ]
    for tid in route:
      if tid == start: in_segment = True
      if in_segment: tids.append(tid)
      if tid == end: break
    return Segment(tids)

  @property
  def id(self):
    return '[%s]:[%s]' % (self.start.id, self.end.id)

  @property
  def name(self):
    if self.start.room is self.end.room:
      return "%s" % self.start.room
    else:
      return "%s to %s" % (self.start.room, self.end.room)

  @property
  def brief_name(self):
    if self.start.room is self.end.room:
      return "%s" % self.start.room
    else:
      return "%s to %s" % (self.start.room.brief_name, self.end.room.brief_name)

  def __str__(self):
    return self.name

  def __repr__(self):
    return "Segment(%s)" % (self.tids)

  def __iter__(self):
    return iter(self.tids)

  def __getitem__(self, key):
    if isinstance(key, slice):
      return Segment(self.tids[key])
    else:
      return self.tids[key]

  def __contains(self, tid):
    return tid in self.tids

  def extend_to(self, tid):
    self.tids.append(tid)
    if self.start is None: self.start = tid
    self.end = tid

  def contains_segment(self, segment):
    return segment.start in self.tids and segment.end in self.tids
