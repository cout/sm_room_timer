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

# This should match WRAM_START in src/defines.asm
WRAM_START = 0x7EFD00 - 0x7E0000

# These should also match the corresponding variables in src/defines.asm
ram_load_preset = WRAM_START + 0x00
ram_gametime_room = WRAM_START + 0x02
ram_last_gametime_room = WRAM_START + 0x04
ram_realtime_room = WRAM_START + 0x06
ram_last_realtime_room = WRAM_START + 0x08
ram_last_room_lag = WRAM_START + 0x0A
ram_last_door_lag_frames = WRAM_START + 0x0C
ram_transition_counter = WRAM_START + 0x0E
ram_transition_flag = WRAM_START + 0x10
ram_last_realtime_door = WRAM_START + 0x12
ram_seg_rt_frames = WRAM_START + 0x14
ram_seg_rt_seconds = WRAM_START + 0x16
ram_seg_rt_minutes = WRAM_START + 0x18
ram_reset_segment_later = WRAM_START + 0x1A

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
      (0x0998, 0x02), # 0x998 to 0x999
      (0x09A4, 0x06), # 0x9A4 to 0x9A9
      (0x09DA, 0x07), # 0x9DA to 0x9E0
      (WRAM_START, 0x20), # 0xFD00 to 0xFD19
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
    collected_beams_bitmask = mem.short(0x9A8)

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
    loading_preset = mem.short(ram_load_preset)
    gametime_room = FrameCount(mem.short(ram_gametime_room))
    last_gametime_room = FrameCount(mem.short(ram_last_gametime_room))
    realtime_room = FrameCount(mem.short(ram_realtime_room))
    last_realtime_room = FrameCount(mem.short(ram_last_realtime_room))
    last_room_lag = FrameCount(mem.short(ram_last_room_lag))
    last_door_lag_frames = FrameCount(mem.short(ram_last_door_lag_frames))
    transition_counter = FrameCount(mem.short(ram_transition_counter))
    last_realtime_door = FrameCount(mem.short(ram_last_realtime_door))
    seg_rt_frames = mem.short(ram_seg_rt_frames)
    seg_rt_seconds = mem.short(ram_seg_rt_seconds)
    seg_rt_minutes = mem.short(ram_seg_rt_minutes)
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
        loading_preset=loading_preset,
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
    loading_preset=None,
    items_bitmask=0,
    beams_bitmask=0,
    items=None,
    beams=None,
    reached_ship=False,
    )
