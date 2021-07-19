from typing import NamedTuple

from frame_count import FrameCount
from rooms import Room, NullRoom
from doors import Door, NullDoor

class TransitionId(object):
  room: Room
  entry_door: Door
  exit_door: Door
  items: str
  beams: str

  def __init__(self, room, entry_door, exit_door, items, beams):
    if room is not entry_door.exit_room and entry_door.exit_room is not NullRoom and room is not NullRoom:
      raise RuntimeError("Expected %s == %s" % (room, entry_door.exit_room))

    if room is not exit_door.entry_room and exit_door.entry_room is not NullRoom and room is not NullRoom:
      # raise RuntimeError("Expected %s == %s" % (room, exit_door.entry_room))
      raise RuntimeError("Entry room for exit door %s should be %s, not %s" % (exit_door, exit_door.entry_room, room))

    self.room = room
    self.entry_door = entry_door
    self.exit_door = exit_door
    self.items = items
    self.beams = beams

  @property
  def entry_room(self):
    return self.entry_door.entry_room

  @property
  def exit_room(self):
    return self.exit_door.exit_room

  def __hash__(self):
    return hash((self.room, self.entry_room, self.exit_room, self.items, self.beams))

  def __eq__(self, other):
    return (self.room, self.entry_room, self.exit_room, self.items, self.beams) == \
           (other.room, other.entry_room, other.exit_room, other.items, other.beams)

  def __repr__(self):
    return '%s (entering from %s via %x, exiting to %s via %x)' % (
        self.room, self.entry_room, self.entry_door.door_id, self.exit_room,
        self.exit_door.door_id)

class TransitionTime(NamedTuple):
  gametime: FrameCount
  realtime: FrameCount
  roomlag: FrameCount
  door: FrameCount

class Transition(NamedTuple):
  id: TransitionId
  time: TransitionTime

  def __repr__(self):
      return "Transition(%s,%s,%s,%s,%s)" % (
        self.id, self.time.gametime,
        self.time.realtime, self.time.roomlag,
        self.time.door)

  @classmethod
  def csv_headers(self):
    return [
      'room_id', 'entry_id', 'exit_id', 'room', 'entry', 'exit',
      'entry_door', 'exit_door', 'items', 'beams', 'gametime', 'realtime',
      'roomlagtime', 'doortime'
    ]

  def as_csv_row(self):
      return (
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
        round(self.time.door.to_seconds(), 3))

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

    transition_id = TransitionId(
        room=room,
        entry_door=entry_door,
        exit_door=exit_door,
        items=row['items'],
        beams=row['beams'])
    transition_time = TransitionTime(
        FrameCount.from_seconds(float(row['gametime'])),
        FrameCount.from_seconds(float(row['realtime'])),
        FrameCount.from_seconds(float(row['roomlagtime'])) if 'roomlagtime' in row else None,
        FrameCount.from_seconds(float(row['doortime'])))
    return Transition(transition_id, transition_time)
