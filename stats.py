import argparse
from tabulate import tabulate

from frame_count import FrameCount
from rooms import Room, Rooms
from history import History, read_history_file

def print_table(table):
  data = + list(zip(names, weights, costs, unit_costs))

  for i, d in enumerate(data):
      line = '|'.join(str(x).ljust(12) for x in d)
      print(line)
      if i == 0:
          print('-' * len(line))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  history = read_history_file(args.filename, rooms)

  table = [ ]
  total_best = FrameCount(0)
  total_median = FrameCount(0)
  total_save = FrameCount(0)
  for id, attempts in history.items():
    # TODO: We should keep stats for real+door, rather than keeping
    # those separately
    n = len(attempts.attempts)
    best = attempts.realtimes.best() + attempts.doortimes.best()
    median = attempts.realtimes.median() + attempts.doortimes.median()
    save = median - best
    total_best += best
    total_median += median
    total_save += save
    table.append([ id, n, best, median, save ]);

  table.append([ 'Total', '', total_best, total_median, total_save ]);

  print(tabulate(table))
