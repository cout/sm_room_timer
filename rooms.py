import json

class Room(object):
  def __init__(self, room_id, name):
    self.room_id = room_id
    self.name = name

  def __repr__(self):
    return self.name

NullRoom = Room(0, 'None')

class Rooms(object):
  def __init__(self, raw_rooms):
    self.rooms = [ Room(room_id=int(room_id, 16), name=room_name)
        for room_id, room_name in raw_rooms.items() ]

    self.by_id = { room.room_id : room for room in self.rooms }
    self.by_name = { room.name : room for room in self.rooms }

    self.add_room(NullRoom)

    self.check_invariants()

  def from_id(self, room_id):
    if type(room_id) is not int:
      raise TypeError("room id should be an int (got %s)" % type(room_id))
    room = self.by_id.get(room_id)
    if room is None:
      room = Room(room_id, hex(room_id))
      self.add_room(room)
    self.check_invariants()
    return room

  def from_name(self, name):
    if name[0:2] == '0x':
      room_id = int(name, 0)
      room = self.from_id(room_id)
    else:
      room = self.by_name.get(name, None)
      if room is None:
        raise RuntimeError("Could not find room with name `%s'" % name)
    self.check_invariants()
    return room

  def add_room(self, room):
    self.by_id[room.room_id] = room
    self.by_name[room.name] = room
    self.check_invariants()

  def check_invariants(self):
    for room in self.by_name.values():
      room2 = self.by_id[room.room_id]
      if room is not room2:
        raise RuntimeError("%s != %s" % (room, room2))
    for room in self.by_id.values():
      room2 = self.by_name[room.name]
      if room is not room2:
        raise RuntimeError("%s != %s" % (room, room2))

  @staticmethod
  def read(filename):
    return Rooms(json.load(open(filename)))
