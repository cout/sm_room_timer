import csv
import statistics

from frame_count import FrameCount
from transition import Transition

class FrameCountList(object):
  def __init__(self):
    self.list = [ ]

  def append(self, frame_count):
    self.list.append(frame_count.count)

  def mean(self):
    return FrameCount(statistics.mean(self.list))

  def median(self):
    return FrameCount(statistics.median(self.list))

  def best(self):
    return FrameCount(min(self.list))

  def __repr__(self):
    return 'avg %s, median %s, best %s' % (self.mean(), self.median(), self.best())

class Attempts(object):
  def __init__(self, transitions=None):
    transitions = transitions or [ ]

    self.attempts = [ ]
    self.gametimes = FrameCountList()
    self.realtimes = FrameCountList()
    self.lagtimes = FrameCountList()
    self.doortimes = FrameCountList()

    for transition in transitions:
      self.append(transition)

  def append(self, transition):
    self.attempts.append(transition)
    self.gametimes.append(transition.time.gametime)
    self.realtimes.append(transition.time.realtime)
    self.lagtimes.append(transition.time.lag)
    self.doortimes.append(transition.time.door)

  def __iter__(self):
    return iter(self.attempts)

  def __len__(self):
    return len(self.attempts)

  def __repr__(self):
    return 'Attempts(%s)' % self.attempts

class History(object):
  def __init__(self, history=None):
    self.history = history or { }

  def record(self, transition):
    attempts = self.history.get(transition.id, None)
    if attempts is None:
      attempts = Attempts()
      self.history[transition.id] = attempts

    attempts.append(transition)

    return attempts

  def __len__(self):
    return len(self.history)

  def __iter__(self):
    return iter(self.history)

  def __repr__(self):
    return 'History(%s)' % repr(self.history)

  def keys(self):
    return self.history.keys()

  def values(self):
    return self.history.values()

  def items(self):
    return self.history.items()

  def __getitem__(self, key):
    return self.history[key]

def history_report(history):
  for tid in sorted(history.keys(), key=lambda tid: (tid.room.room_id, tid.exit_room.room_id)):
    print("%s: %s (%s/%s to %s/%s)" % (tid, len(history[tid]),
      tid.room.room_id, id(tid.room), tid.exit_room.room_id,
      id(tid.exit_room)))
  print()

def read_history_file(filename, rooms, doors):
  history = History()
  with open(filename) as csvfile:
    reader = csv.DictReader(csvfile)
    n = 0
    for row in reader:
      n += 1
      try:
        transition = Transition.from_csv_row(rooms, doors, row)
      except Exception as e:
        raise RuntimeError("Error reading history file, line %d" % n) from e
      history.record(transition)
  print("Read history for {} rooms.".format(len(history)))
  return history

