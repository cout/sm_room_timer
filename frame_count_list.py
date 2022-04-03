from frame_count import FrameCount

from scipy import stats

import statistics

class FrameCountList(object):
  def __init__(self):
    self._list = [ ]
    self._values = [ ]
    self._best = FrameCount.max
    self._prev_best = FrameCount.max

  def append(self, frame_count):
    if frame_count is not None and frame_count <= self._best:
      self._prev_best = self._best
      self._best = frame_count
    self._list.append(frame_count.count if frame_count is not None else None)
    if frame_count is not None: self._values.append(frame_count.count)

  def mean(self):
    return FrameCount(statistics.mean(self.values()))

  def median(self):
    return FrameCount(statistics.median(self.values()))

  def best(self):
    return self._best

  def prev_best(self):
    return self._prev_best

  def most_recent(self):
    return FrameCount(self.values()[-1])

  def percentile(self, p):
    return FrameCount(stats.scoreatpercentile(self.values(), p))

  def as_percentiles(self):
    l = self.values()
    d = { val: len(l) - idx - 1 for idx, val in enumerate(reversed(sorted(l))) }
    p = { x: 100.0 * d[x] / (len(l) - 1) for x in sorted(l) }
    return p

  def values(self):
    return self._values

  def __repr__(self):
    return 'avg %s, median %s, best %s' % (self.mean(), self.median(), self.best())
