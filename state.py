from frame_count import FrameCount
from memory import MemoryRegion, SparseMemory
from rooms import NullRoom
from doors import NullDoor
from game_states import GameStates

def items_string(imask):
  a = [
    's' if (imask & 0x2000) else '.', # speed
    'b' if (imask & 0x1000) else '.', # bombs
    '@' if (imask & 0x0200) else '.', # space jump
    'h' if (imask & 0x0100) else '.', # hi jump boots
    'g' if (imask & 0x0020) else '.', # gravity
    '*' if (imask & 0x0008) else '.', # screw attack
    'm' if (imask & 0x0004) else '.', # morph ball
    '#' if (imask & 0x0002) else '.', # spring ball
    '.' if (imask & 0x0001) else '.', # varia
  ]

  return ''.join(a)

def beams_string(bmask, imask):
  a = [
    'X' if (imask & 0x8000) else '.', # x-ray
    'G' if (imask & 0x4000) else '.', # grapple
    'C' if (bmask & 0x1000) else '.', # charge
    'P' if (bmask & 0x0008) else '.', # plasma
    'S' if (bmask & 0x0004) else '.', # spazer
    'I' if (bmask & 0x0002) else '.', # ice
    'W' if (bmask & 0x0001) else '.', # wave
  ]

  return ''.join(a)

class State(object):
  def __init__(self, **attrs):
    for name in attrs:
      setattr(self, name, attrs[name])

  def __repr__(self):
    return "State(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  @staticmethod
  def read_from(sock, rooms, doors, read_ship_state=False):
    addresses = [
      (0x078D, 0x10), # 0x78D to 0x79C
      (0x0998, 0x10), # 0x998 to 0x9A7
      (0x09DA, 0x07), # 0x9DA to 0x9E0
      (0xFB00, 0x20), # 0xFB00 to 0xFB19
    ]

    if read_ship_state:
      addresses.extend([
        (0xD821, 0x01),
        (0x0FB2, 0x02),
      ])

    mem = SparseMemory.read_from(sock, *addresses)
    if mem is None:
      return None

    door_id = mem.short(0x78D)
    room_id = mem.short(0x79B)
    door = doors.from_id(door_id)
    room = rooms.from_id(room_id)

    game_state_id = mem.short(0x998)
    game_state = GameStates.get(game_state_id, hex(game_state_id))

    collected_items_bitmask = mem.short(0x9A4)
    collected_beams_bitmask = mem.short(0x9A6)

    igt_frames = mem.short(0x9DA)
    igt_seconds = mem[0x9DC]
    igt_minutes = mem[0x9DE]
    igt_hours = mem[0x9E0]
    fps = 60.0 # TODO
    igt = FrameCount(216000 * igt_hours + 3600 * igt_minutes + 60 * igt_seconds + igt_frames)

    if read_ship_state:
      event_flags = mem[0xD821]
      ship_ai = mem.short(0xFB2)
      reached_ship = (event_flags & 0x40) > 0 and ship_ai == 0xaa4f
    else:
      reached_ship = False

    # Practice hack
    gametime_room = FrameCount(mem.short(0x0FB02))
    last_gametime_room = FrameCount(mem.short(0x0FB04))
    realtime_room = FrameCount(mem.short(0x0FB06))
    last_realtime_room = FrameCount(mem.short(0x0FB08))
    last_room_lag = FrameCount(mem.short(0x0FB0A))
    last_door_lag_frames = FrameCount(mem.short(0x0FB0C))
    transition_counter = FrameCount(mem.short(0x0FB0E))
    last_realtime_door = FrameCount(mem.short(0x0FB12))
    ram_load_preset = mem.short(0x0FB00)
    seg_rt_frames = mem.short(0x0FB14)
    seg_rt_seconds = mem.short(0x0FB16)
    seg_rt_minutes = mem.short(0x0FB18)
    seg_rt = FrameCount(3600 * seg_rt_minutes + 60 * seg_rt_seconds + seg_rt_frames)

    return State(
        door=door,
        room=room,
        game_state_id=game_state_id,
        game_state=game_state,
        igt=igt,
        seg_rt=seg_rt,
        gametime_room=gametime_room,
        last_gametime_room=last_gametime_room,
        realtime_room=realtime_room,
        last_realtime_room=last_realtime_room,
        last_realtime_door=last_realtime_door,
        last_room_lag=last_room_lag,
        last_door_lag_frames=last_door_lag_frames,
        transition_counter=transition_counter,
        ram_load_preset=ram_load_preset,
        items_bitmask='%x' % collected_items_bitmask,
        beams_bitmask='%x' % collected_beams_bitmask,
        items=items_string(imask=collected_items_bitmask),
        beams=beams_string(imask=collected_items_bitmask, bmask=collected_beams_bitmask),
        reached_ship=reached_ship,
        )

NullState = State(
    door=NullDoor,
    room=NullRoom,
    game_state=None,
    event_flags=0,
    ship_ai=0,
    igt=FrameCount(0),
    seg_rt=FrameCount(0),
    gametime_room=None,
    last_gametime_room=None,
    realtime_room=None,
    last_realtime_room=None,
    last_door_lag_frames=None,
    transition_counter=None,
    last_room_lag=None,
    ram_load_preset=None,
    items_bitmask=0,
    beams_bitmask=0,
    items=None,
    beams=None,
    reached_ship=False,
    )
