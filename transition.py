from typing import NamedTuple

from frame_count import FrameCount
from rooms import Room, NullRoom
from doors import Door, NullDoor

import datetime
from dataclasses import dataclass
import re

@dataclass
class TransitionId(object):
  room: Room
  entry_door: Door
  exit_door: Door
  items: str
  beams: str

  def __init__(self, room, entry_door, exit_door, items, beams):
    self.room = room
    self.entry_door = entry_door
    self.exit_door = exit_door
    self.items = items
    self.beams = beams

    if room is not entry_door.exit_room and entry_door.exit_room is not NullRoom and room is not NullRoom:
      raise RuntimeError("Expected %s == %s: %s" % (room, entry_door.exit_room, self))

    if room is not exit_door.entry_room and exit_door.entry_room is not NullRoom and room is not NullRoom:
      # raise RuntimeError("Expected %s == %s" % (room, exit_door.entry_room))
      raise RuntimeError("Entry room for exit door %s should be %s, not %s" % (exit_door, exit_door.entry_room, room))

  @property
  def entry_room(self):
    return self.entry_door.entry_room

  @property
  def exit_room(self):
    return self.exit_door.exit_room

  @property
  def id(self):
    return '%x|%x|%x|%s|%s' % (self.room.room_id,
        self.entry_door.door_id, self.exit_door.door_id, self.items,
        self.beams)

  @classmethod
  def from_id(cls, id, rooms, doors):
    m = re.match(r'(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*)', id)
    if m:
      s = m.group(1).upper()
      room = rooms.by_id[int(m.group(1), 16)]
      entry_door = doors.by_id[int(m.group(2), 16)]
      exit_door = doors.by_id[int(m.group(3), 16)]
      items = m.group(4)
      beams = m.group(5)
      return cls(room, entry_door, exit_door, items, beams)

    else:
      return None

  def __hash__(self):
    return hash((self.room, self.entry_room, self.exit_room, self.items, self.beams))

  def __eq__(self, other):
    return self.room is other.room and self.entry_room is other.entry_room and self.exit_room is other.exit_room and self.items == other.items and self.beams == other.beams

  def __str__(self):
    return '%s (entering from %s via %x, exiting to %s via %x)' % (
        self.room, self.entry_room, self.entry_door.door_id, self.exit_room,
        self.exit_door.door_id)

  def __repr__(self):
    return 'TransitionId(%s,%s,%s,items=%s,beams=%s)' % (
        repr(self.room), repr(self.entry_door), repr(self.exit_door),
        repr(self.items), repr(self.beams))

class TransitionTime(NamedTuple):
  gametime: FrameCount
  realtime: FrameCount
  roomlag: FrameCount
  doorlag: FrameCount
  realtime_door: FrameCount

  # Older versions did not save real doortime, so we need to track
  # whether the value was faked when it was read in to avoid treating a
  # faked doortime as a real one.
  doortime_is_real: bool

  def __add__(self, t):
    return TransitionTime(
        gametime=(self.gametime + t.gametime),
        realtime=(self.realtime + t.realtime),
        roomlag=(self.roomlag + t.roomlag),
        doorlag=(self.doorlag + t.doorlag),
        realtime_door=(self.realtime_door + t.realtime_door),
        doortime_is_real=(self.doortime_is_real and t.doortime_is_real))

  @property
  def totalrealtime(self):
    return self.realtime + self.realtime_door

class Transition(NamedTuple):
  ts: datetime.datetime
  id: TransitionId
  time: TransitionTime

  def __repr__(self):
      return "Transition(%s,%s,%s,%s,%s,%s)" % (
        self.id, self.time.gametime,
        self.time.realtime, self.time.roomlag,
        self.time.doorlag, self.time.realtime_door)

  @classmethod
  def csv_headers(self):
    return [
      'timestamp', 'room_id', 'entry_id', 'exit_id', 'room', 'entry',
      'exit', 'entry_door', 'exit_door', 'items', 'beams', 'gametime',
      'realtime', 'roomlagtime', 'doorrealtime', 'doorlagtime'
    ]

  def as_csv_row(self):
    return (
      self.ts.isoformat(),
      '%04x' % self.id.room.room_id,
      '%04x' % self.id.entry_room.room_id,
      '%04x' % self.id.exit_room.room_id,
      self.id.room,
      self.id.entry_room,
      self.id.exit_room,
      '%04x' % self.id.entry_door.door_id,
      '%04x' % self.id.exit_door.door_id,
      self.id.items,
      self.id.beams,
      round(self.time.gametime.to_seconds(), 3),
      round(self.time.realtime.to_seconds(), 3),
      round(self.time.roomlag.to_seconds(), 3),
      round(self.time.realtime_door.to_seconds(), 3) if self.time.doortime_is_real else None,
      round(self.time.doorlag.to_seconds(), 3))

  @classmethod
  def from_csv_row(self, rooms, doors, row):
    room = rooms.from_id(int(row['room_id'], 16))

    entry_door_id = int(row.get('entry_door', '0'), 16)
    if entry_door_id == 0:
      entry_room = rooms.from_id(int(row['entry_id'], 16))
      entry_door = doors.from_terminals(entry_room, room)
    else:
      entry_door = doors.from_id(entry_door_id)

    exit_door_id = int(row.get('exit_door', '0'), 16)
    if exit_door_id == 0:
      exit_room = rooms.from_id(int(row['exit_id'], 16))
      exit_door = doors.from_terminals(room, exit_room)
    else:
      exit_door = doors.from_id(exit_door_id)

    ts = row.get('timestamp', None)
    if ts is not None:
      ts = datetime.datetime.fromisoformat(ts)
    else:
      ts = datetime.datetime.fromtimestamp(0)

    doorlag_seconds = row.get('doorlagtime', None) or row['doortime']
    doorlagtime = FrameCount.from_seconds(float(doorlag_seconds))

    doorreal_seconds = row.get('doorrealtime', None)
    if doorreal_seconds is not None and doorreal_seconds != '':
      doorrealtime = FrameCount.from_seconds(float(doorreal_seconds))
      doortime_is_real = True
    else:
      doorrealtime = FrameCount(120) + doorlagtime
      doortime_is_real = False

    transition_id = TransitionId(
        room=room,
        entry_door=entry_door,
        exit_door=exit_door,
        items=row['items'],
        beams=row['beams'])
    if 'lagtime' in row and not 'roomlagtime' in row:
      row['roomlagtime'] = row['lagtime']
    transition_time = TransitionTime(
        gametime=FrameCount.from_seconds(float(row['gametime'])),
        realtime=FrameCount.from_seconds(float(row['realtime'])),
        roomlag=FrameCount.from_seconds(float(row['roomlagtime'])) if 'roomlagtime' in row else None,
        doorlag=doorlagtime,
        realtime_door=doorrealtime,
        doortime_is_real=doortime_is_real)
    return Transition(ts, transition_id, transition_time)
