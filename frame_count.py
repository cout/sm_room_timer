import sys

from functools import total_ordering

@total_ordering
class FrameCount(object):
  def __init__(self, count):
    self.count = count

  def to_seconds(self):
    return self.count / 60.0

  @classmethod
  def from_seconds(cls, secs):
    return cls(round(secs * 60, 0))

  @classmethod
  def parse(cls, s):
    secs, frames = s.split("'")
    return cls(int(secs)*60 + int(frames))

  def __eq__(self, other):
    return self.count == other.count

  def __lt__(self, other):
    return self.count < other.count

  def __add__(self, other):
    return FrameCount(self.count + other.count)

  def __sub__(self, other):
    return FrameCount(self.count - other.count)

  def __repr__(self):
    sign = '-' if self.count < 0 else ''
    count = abs(self.count)
    if count / 60 < 60:
      return '%s%d\'%02d' % (sign, count / 60, count % 60)
    else:
      return '%s%d:%02d\'%02d' % (sign, count / 60 / 60, (count / 60) % 60, abs(count) % 60)

FrameCount.max = FrameCount(sys.maxsize)
