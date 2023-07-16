from rooms import NullRoom
from frame_count import FrameCount

def is_preset(state):
  # TODO: explain why this is here
  if state.game_state != 'NormalGameplay': return False

  # TODO: explain why this is here
  if state.room.name == 'Ceres Elevator': return False

  # TODO: explain why this is here (the tourian escape preset does not
  # clear out the last_realtime_room counter)
  if state.room.name == 'Mother Brain' and state.last_realtime_room <= FrameCount(16): return True

  # TODO: explain why this is here
  if state.last_realtime_room == FrameCount(0): return True

  return False

class StateChange(object):
  def __init__(self, prev_state, state, current_room):
    self.prev_state = prev_state
    self.state = state
    self.is_room_change = state.game_state == 'NormalGameplay' and current_room is not state.room
    self.is_program_start = self.is_room_change and current_room is NullRoom
    self.transition_finished = state.game_state == 'NormalGameplay' and prev_state.game_state == 'DoorTransition'
    self.escaped_ceres = state.game_state == 'StartOfCeresCutscene' and prev_state.game_state == 'NormalGameplay' and state.room.name == 'Ceres Elevator'
    self.reached_ship = state.reached_ship and not prev_state.reached_ship
    self.is_reset = state.igt < prev_state.igt
    self.is_preset = is_preset(state)
    self.is_loading_preset = prev_state.loading_preset != state.loading_preset and state.loading_preset != 0
    self.door_changed = prev_state.door != state.door
    self.game_state_changed = prev_state.game_state != state.game_state
    self.is_playing = state.game_state_id >= 0x08 and state.game_state_id <= 0x18

  def __repr__(self):
    return "StateChange(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  def description(self):
    changes = [ ]

    if self.is_program_start:
      changes.append("Starting in room %s at %s, door=%s" % (
        self.state.room, self.state.igt, self.state.door))
    elif self.is_room_change and self.transition_finished:
      changes.append("Transition to %s (%x) at %s using door %s" % (
          self.state.room, self.state.room.room_id,
          self.state.igt, self.state.door))
    elif self.reached_ship:
      changes.append("Reached ship at %s" % (self.state.igt))
    elif self.is_room_change:
      changes.append("Room changed to %s (%x) at %s without using a door" % (
        self.state.room, self.state.room.room_id,
        self.state.igt))

    if self.is_reset:
      changes.append("Reset detected to %s" % self.state.igt)

    if self.door_changed:
      changes.append("Door changed to %s at %s" % (self.state.door, self.state.igt))

    if self.game_state_changed:
      changes.append("Game state changed to %s at %s" % (
        self.state.game_state, self.state.igt))

    return changes

