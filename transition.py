from typing import NamedTuple

from frame_count import FrameCount
from rooms import Room

class TransitionId(object):
  room: Room
  entry_room: Room
  exit_room: Room
  items: str
  beams: str

  def __init__(self, room, entry_room, exit_room, items, beams):
    self.room = room
    self.entry_room = entry_room
    self.exit_room = exit_room
    self.items = items
    self.beams = beams

  def __hash__(self):
    return hash((self.room, self.entry_room, self.exit_room, self.items, self.beams))

  def __eq__(self, other):
    return (self.room, self.entry_room, self.exit_room, self.items, self.beams) == \
           (other.room, other.entry_room, other.exit_room, other.items, other.beams)

  def __repr__(self):
    return '%s (entering from %s, exiting to %s)' % (self.room, self.entry_room, self.exit_room)

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
    return [ 'room_id', 'entry_id', 'exit_id', 'room', 'entry', 'exit', 'items', 'beams', 'gametime', 'realtime', 'lagtime', 'doortime' ]

  def as_csv_row(self):
      return (
        '%04x' % self.id.room.room_id,
        '%04x' % self.id.entry_room.room_id,
        '%04x' % self.id.exit_room.room_id,
        self.id.room,
        self.id.entry_room,
        self.id.exit_room,
        self.id.items,
        self.id.beams,
        round(self.time.gametime.to_seconds(), 3),
        round(self.time.realtime.to_seconds(), 3),
        round(self.time.lag.to_seconds(), 3),
        round(self.time.door.to_seconds(), 3))

  @classmethod
  def from_csv_row(self, rooms, row):
    transition_id = TransitionId(
        room=rooms.from_id(int(row['room_id'], 16)),
        entry_room=rooms.from_id(int(row['entry_id'], 16)),
        exit_room=rooms.from_id(int(row['exit_id'], 16)),
        items=row['items'],
        beams=row['beams'])
    transition_time = TransitionTime(
        FrameCount.from_seconds(float(row['gametime'])),
        FrameCount.from_seconds(float(row['realtime'])),
        FrameCount.from_seconds(float(row['lagtime'])),
        FrameCount.from_seconds(float(row['doortime'])))
    return Transition(transition_id, transition_time)
