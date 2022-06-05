class Segment(object):
  def __init__(self, tids=None):
    self.tids = tids or []

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
  def start(self):
    return self.tids[0]

  @property
  def end(self):
    return self.tids[-1]

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

  def extend_to(self, tid):
    self.tids.append(tid)

