#!/usr/bin/env python3

import datetime
import time
import argparse
import statistics
import csv
import os.path
from functools import total_ordering
from typing import NamedTuple

from retroarch.network_command_socket import NetworkCommandSocket
from memory_region import MemoryRegion
from rooms import Room, Rooms
from areas import Areas
from game_states import GameStates

@total_ordering
class FrameCount(object):
  def __init__(self, count):
    self.count = count

  def to_seconds(self):
    return self.count / 60.0

  @classmethod
  def from_seconds(cls, secs):
    return cls(secs * 60)

  def __eq__(self, other):
    return self.count == other.count

  def __lt__(self, other):
    return self.count < other.count

  def __repr__(self):
    return '%d\'%02d' % (self.count / 60, self.count % 60)

class TransitionId(object):
  room: Room
  from_room: Room
  to_room: Room

  def __init__(self, room, from_room, to_room):
    self.room = room
    self.from_room = from_room
    self.to_room = to_room

  def __hash__(self):
    return hash((self.room, self.to_room))

  def __eq__(self, other):
    return (self.room, self.to_room) == (other.room, other.to_room)

  def __repr__(self):
    return '%s (exiting to %s)' % (self.room, self.to_room)

class TransitionTime(NamedTuple):
  gametime: FrameCount
  realtime: FrameCount
  lag: FrameCount
  door: FrameCount

class Transition(NamedTuple):
  id: TransitionId
  time: TransitionTime

  def __repr__(self):
      return "Transition(%s,%s,%s,%s,%s)" % (
        self.id, self.time.gametime,
        self.time.realtime, self.time.lag,
        self.time.door)

  @classmethod
  def csv_headers(self):
    return [ 'room', 'exit', 'gametime', 'realtime', 'lagtime', 'doortime' ]

  def as_csv_row(self):
      return (
        self.id.room, self.id.to_room, self.time.gametime.to_seconds(),
        self.time.realtime.to_seconds(), self.time.lag.to_seconds(),
        self.time.door.to_seconds())

  @classmethod
  def from_csv_row(self, rooms, row):
    transition_id = TransitionId(
        room=rooms.from_name(row['room']),
        to_room=rooms.from_name(row['exit']),
        from_room=None)
    transition_time = TransitionTime(
        FrameCount.from_seconds(float(row['gametime'])),
        FrameCount.from_seconds(float(row['realtime'])),
        FrameCount.from_seconds(float(row['lagtime'])),
        FrameCount.from_seconds(float(row['doortime'])))
    return Transition(transition_id, transition_time)

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
  for tid in sorted(history.keys(), key=lambda tid: (tid.room.room_id, tid.to_room.room_id)):
    a = history[tid]
    # str(tid)
    # str(len(a))
    # str(tid.room.room_id)
    # str(id(tid.room))
    # str(tid.to_room.room_id)
    # str(id(tid.to_room))
    print("%s: %s (%s/%s to %s/%s)" % (tid, len(a),
      tid.room.room_id, id(tid.room), tid.to_room.room_id,
      id(tid.to_room)))
  print()

def read_history_file(filename, rooms):
  history = History()
  with open(filename) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
      transition = Transition.from_csv_row(rooms, row)
      history.record(transition)
  # print(history)
  # history_report(history)
  print("Read history for {} rooms.".format(len(history)))
  return history

class Store(object):
  def __init__(self, rooms, filename=None):
    if filename is not None and os.path.exists(filename):
      self.history = read_history_file(filename, rooms)
    else:
      self.history = History()

    if filename is not None:
      self.file = open(filename, 'a')
      self.writer = csv.writer(self.file)
      if len(self.history) == 0:
        print(','.join(Transition.csv_headers()), file=self.file)
    else:
      self.file = None
      self.writer = None

  def colorize(self, ttime, atimes):
    p0 = atimes.best()
    p50 = atimes.median()
    p25_est = FrameCount.from_seconds((p0.to_seconds() + p50.to_seconds()) / 2.0)
    p75_est = FrameCount.from_seconds(p50.to_seconds() + (p50.to_seconds() - p25_est.to_seconds()))

    color = 7
    if ttime <= p0:
      color = 214
    elif ttime <= p25_est:
      color = 40
    elif ttime <= p50:
      color = 148
    elif ttime <= p75_est:
      color = 204
    else:
      color = 196

    return "\033[38;5;%sm%s\033[m (%s)" % (color, ttime, atimes)

  def transitioned(self, transition):
    attempts = self.history.record(transition)
    # history_report(self.history)

    if self.writer is not None:
      self.writer.writerow(transition.as_csv_row())
      self.file.flush()

    print('%s #%s:' % (transition.id, len(attempts)))
    print('Game: %s' % self.colorize(transition.time.gametime, attempts.gametimes))
    print('Real: %s' % self.colorize(transition.time.realtime, attempts.realtimes))
    print('Lag:  %s' % self.colorize(transition.time.lag, attempts.lagtimes))
    print('Door: %s' % self.colorize(transition.time.door, attempts.doortimes))
    print('')

  def close(self):
    self.file.close()

class RoomTimer(object):
  def __init__(self, rooms, store):
    self.sock = NetworkCommandSocket()
    self.rooms = rooms
    self.store = store
    self.current_room = None
    self.last_last_room = None
    self.last_room = None
    self.prev_game_state = None
    self.prev_igt = datetime.timedelta(0)
    self.ignore_next_transition = False

  def poll(self):
    region1 = MemoryRegion.read_from(self.sock, 0x0790, 0x1f)
    region2 = MemoryRegion.read_from(self.sock, 0x0990, 0xef)
    # region3 = MemoryRegion.read_from(self.sock, 0xD800, 0x8f)
    # region4 = MemoryRegion.read_from(self.sock, 0x0F80, 0x4f)
    # region5 = MemoryRegion.read_from(self.sock, 0x05B0, 0x0f)
    region6 = MemoryRegion.read_from(self.sock, 0x1FB00, 0x100)

    room_id = region1.short(0x79B)
    room = self.rooms.from_id(room_id)

    region_id = region1.short(0x79F) 
    area = Areas.get(region_id, hex(region_id))

    game_state_id = region2.short(0x998)
    game_state = GameStates.get(game_state_id, hex(game_state_id))

    igt_frames = region2.short(0x9DA)
    igt_seconds = region2[0x9DC]
    igt_minutes = region2[0x9DE]
    igt_hours = region2[0x9E0]
    fps = 60.0 # TODO
    igt = datetime.timedelta(seconds=igt_hours * 3600 + igt_minutes
        * 60 + igt_seconds + igt_frames / fps)

    # Practice hack
    gametime_room = FrameCount(region6.short(0x1FB00))
    last_gametime_room = FrameCount(region6.short(0x1FB02))
    realtime_room = FrameCount(region6.short(0x1FB44))
    last_realtime_room = FrameCount(region6.short(0x1FB46))
    last_door_lag_frames = FrameCount(region6.short(0x1FB10))
    transition_counter = FrameCount(region6.short(0x1FB0E))
    last_lag_counter = FrameCount(region6.short(0x1FB98))

    if game_state != self.prev_game_state:
      # print("Game state changed to %s at time %s" % (game_state, igt))
      # print('')
      pass

    if game_state == 'normalGameplay' and self.current_room is not room:
      self.last_last_room = self.last_room
      self.last_room = self.current_room
      self.current_room = room

    if igt < self.prev_igt and game_state == 'doorTransition':
      # print('Reset detected (%s < %s); igoring next transition' %
          # (gametime_room, self.prev_igt))
      self.ignore_next_transition = True

    if self.prev_game_state == 'doorTransition' and game_state == 'normalGameplay':
      if self.ignore_next_transition:
        # print('Ignoring this transition')
        pass
      else:
        transition_id = TransitionId(
            self.last_room, self.last_last_room, self.current_room)
        transition_time = TransitionTime(
            last_gametime_room, last_realtime_room, last_lag_counter,
            last_door_lag_frames)
        transition = Transition(transition_id, transition_time)
        self.store.transitioned(transition)
      self.ignore_next_transition = False

    self.prev_game_state = game_state
    self.prev_igt = igt

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  store = Store(rooms, args.filename)
  timer = RoomTimer(rooms, store)

  while True:
    timer.poll()
    time.sleep(1.0/60)
