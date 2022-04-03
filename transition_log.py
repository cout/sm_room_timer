from transition import Transition

import csv

class FileTransitionLog(object):
  def __init__(self, filename):
    self.file = open(filename, 'a')
    self.writer = csv.writer(self.file)
    if self.file.tell() == 0:
      self._write_header()

  def _write_header(self):
    print(','.join(Transition.csv_headers()), file=self.file)

  def write_transition(self, transition):
    self.writer.writerow(transition.as_csv_row())
    self.file.flush()

  def close(self):
    self.file.close()

class NullTransitionLog(object):
  def __init__(self):
    pass

  def write_transition(self, transition):
    pass

  def close(self):
    pass
