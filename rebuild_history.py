#!/usr/bin/env python3

from transition import Transition
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor

import argparse
import csv

def need_rebuild(filename):
  with open(filename) as infile:
    reader = csv.DictReader(infile)
    return reader.fieldnames != Transition.csv_headers()

def rebuild_history(rooms, doors, input_filenames, output_filename):
  # Some older files don't have door ids, so we need to infer the door
  # ids from the room ids
  by_room_and_exit = { }
  for input in input_filenames:
    with open(input) as infile:
      reader = csv.DictReader(infile)
      for row in reader:
        transition = Transition.from_csv_row(rooms, doors, row)
        if transition.id.entry_room is NullRoom:
          # print("ignoring %s" % transition.id)
          continue
        key = (transition.id.room, transition.id.exit_room)
        r = by_room_and_exit.get(key)
        if r is None:
          by_room_and_exit[key] = { }
          by_room_and_exit[key][transition.id] = True

  with open(output_filename, 'w') as outfile:
    print(','.join(Transition.csv_headers()), file=outfile)
    writer = csv.writer(outfile)

    for input in input_filenames:
      with open(input) as infile:
        reader = csv.DictReader(infile)
        n = 1 # we already read the header
        for row in reader:
          n += 1
          transition = Transition.from_csv_row(rooms, doors, row)
          if transition.id.entry_door.entry_room is NullRoom:
            key = (transition.id.room, transition.id.exit_room)
            l = by_room_and_exit.get(key)
            if l:
              if len(l) == 1:
                print("Fixing entry door on line %d" % n)
                transition.id.entry_door = list(l.keys())[0].entry_door
              else:
                print("More than one entry door found for %s to $s (line %d): %s" %
                    (transition.id.room, transition.id.exit_room, n,
                      repr(l)))
            else:
              # print("No entry door found for %s to %s (line %d)" %
              #     (transition.id.room, transition.id.exit_room, n))
              pass
          writer.writerow(transition.as_csv_row())

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-i', '--input', dest='inputs', action='append')
  parser.add_argument('-o', '--output', dest='output', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)

  rebuild_history(rooms, doors, args.inputs, args.output)
