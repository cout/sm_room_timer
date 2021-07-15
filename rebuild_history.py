#!/usr/bin/env python3

from transition import Transition
from rooms import Rooms
from doors import Doors

import argparse
import csv

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-i', '--input', dest='input', default=None)
  parser.add_argument('-o', '--output', dest='output', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)

  with open(args.input) as infile:
    with open(args.output, 'w') as outfile:
      print(','.join(Transition.csv_headers()), file=outfile)
      reader = csv.DictReader(infile)
      writer = csv.writer(outfile)
      for row in reader:
        transition = Transition.from_csv_row(rooms, doors, row)
        writer.writerow(transition.as_csv_row())
