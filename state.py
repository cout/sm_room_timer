from frame_count import FrameCount
from memory import MemoryRegion
from areas import Areas
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
  def read_from(sock, rooms, doors):
    region1 = MemoryRegion.read_from(sock, 0x0770, 0x3f)
    region2 = MemoryRegion.read_from(sock, 0x0990, 0xef)
    region3 = MemoryRegion.read_from(sock, 0xD800, 0x8f)
    region4 = MemoryRegion.read_from(sock, 0x0F80, 0x4f)
    # region5 = MemoryRegion.read_from(sock, 0x05B0, 0x0f)
    region6 = MemoryRegion.read_from(sock, 0x1FB00, 0x120)

    door_id = region1.short(0x78D)
    room_id = region1.short(0x79B)
    door = doors.from_id(door_id)
    room = rooms.from_id(room_id)

    region_id = region1.short(0x79F) 
    area = Areas.get(region_id, hex(region_id))

    game_state_id = region2.short(0x998)
    game_state = GameStates.get(game_state_id, hex(game_state_id))

    collected_items_bitmask = region2.short(0x9A4)
    collected_beams_bitmask = region2.short(0x9A8)

    igt_frames = region2.short(0x9DA)
    igt_seconds = region2[0x9DC]
    igt_minutes = region2[0x9DE]
    igt_hours = region2[0x9E0]
    fps = 60.0 # TODO
    igt = FrameCount(216000 * igt_hours + 3600 * igt_minutes + 60 * igt_seconds + igt_frames)

    event_flags = region3.short(0xD821)
    ship_ai = region4.short(0xFB2)

    # Practice hack
    gametime_room = FrameCount(region6.short(0x1FB00))
    last_gametime_room = FrameCount(region6.short(0x1FB04))
    realtime_room = FrameCount(region6.short(0x1FB06))
    last_realtime_room = FrameCount(region6.short(0x1FB08))
    last_room_lag = FrameCount(region6.short(0x1FB0A))
    last_door_lag_frames = FrameCount(region6.short(0x1FB0C))
    transition_counter = FrameCount(region6.short(0x1FB0E))
    ram_load_preset = region6.short(0x1FC00)
    seg_rt_frames = region6.short(0x1FB14)
    seg_rt_seconds = region6.short(0x1FB16)
    seg_rt_minutes = region6.short(0x1FB18)
    seg_rt = FrameCount(3600 * seg_rt_minutes + 60 * seg_rt_seconds + seg_rt_frames)

    return State(
        door=door,
        room=room,
        area=area,
        game_state_id=game_state_id,
        game_state=game_state,
        event_flags=event_flags,
        ship_ai=ship_ai,
        igt=igt,
        seg_rt=seg_rt,
        gametime_room=gametime_room,
        last_gametime_room=last_gametime_room,
        realtime_room=realtime_room,
        last_realtime_room=last_realtime_room,
        last_room_lag=last_room_lag,
        last_door_lag_frames=last_door_lag_frames,
        transition_counter=transition_counter,
        ram_load_preset=ram_load_preset,
        items_bitmask='%x' % collected_items_bitmask,
        beams_bitmask='%x' % collected_beams_bitmask,
        items=items_string(imask=collected_items_bitmask),
        beams=beams_string(imask=collected_items_bitmask, bmask=collected_beams_bitmask),
        )

NullState = State(
    door=NullDoor,
    room=NullRoom,
    area='',
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
    items=None,
    beams=None,
    )
