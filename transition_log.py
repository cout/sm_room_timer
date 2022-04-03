from transition import Transition
from history import History

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

def read_transition_log_csv_incrementally(csvfile, rooms, doors):
  history = History()
  reader = csv.DictReader(csvfile)
  n = 1 # start at 1 for the header
  for row in reader:
    n += 1
    try:
      action = 'reading history file'
      transition = Transition.from_csv_row(rooms, doors, row)
      action = 'recording transition'
      history.record(transition, from_file=True)
      yield history, transition
    except Exception as e:
      raise RuntimeError("Error %s, line %d\nrow: %s" % (action, n, row)) from e
  return history

def read_transition_log_incrementally(filename, rooms, doors):
  with open(filename) as csvfile:
    for history, transition in read_transition_log_csv_incrementally(csvfile, rooms, doors):
      yield history, transition

def read_transition_log(filename, rooms, doors):
  for history, transition in read_transition_log_incrementally(filename, rooms, doors):
    pass
  print("Read history for {} rooms.".format(len(history)))
  return history
