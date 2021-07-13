#!/usr/bin/env python3

import datetime
import time
import argparse
import csv
import os.path

from retroarch.network_command_socket import NetworkCommandSocket
from memory_region import MemoryRegion
from rooms import Room, Rooms, NullRoom
from areas import Areas
from game_states import GameStates
from frame_count import FrameCount
from transition import TransitionId, TransitionTime, Transition
from history import History, read_history_file

class Store(object):
  def __init__(self, rooms, filename=None):
    if filename is not None and os.path.exists(filename):
      self.history = read_history_file(filename, rooms)
    else:
      self.history = History()

    if filename is not None:
      self.file = open(filename, 'a')
      self.writer = csv.writer(self.file)
      # TODO: this incorrectly appends headers to a file that only has a header line
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

    color = 8
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

class Timeline(object):
  def __init__(self):
    self.transitions = [ ]

  def transitioned(self, igt, transition):
    self.transitions.append((igt, transition.id))

  def last_transition(self):
    if len(self.transitions) > 0:
      return self.transitions[-1][1]
    else:
      return None

  def last_transition_before(self, igt):
    return next(lambda t: t[0] < igt, reversed(self.transitions))[1]

  def reset(self, igt):
    self.transitions = [ t for t in self.transitions if t[0] < igt ]

  def __repr__(self):
    return 'Timeline(%s)' % repr(self.transitions)

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

  @staticmethod
  def read_from(sock, rooms):
    region1 = MemoryRegion.read_from(sock, 0x0790, 0x1f)
    region2 = MemoryRegion.read_from(sock, 0x0990, 0xef)
    # region3 = MemoryRegion.read_from(sock, 0xD800, 0x8f)
    # region4 = MemoryRegion.read_from(sock, 0x0F80, 0x4f)
    # region5 = MemoryRegion.read_from(sock, 0x05B0, 0x0f)
    region6 = MemoryRegion.read_from(sock, 0x1FB00, 0x100)

    room_id = region1.short(0x79B)
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

    # Practice hack
    gametime_room = FrameCount(region6.short(0x1FB00))
    last_gametime_room = FrameCount(region6.short(0x1FB02))
    realtime_room = FrameCount(region6.short(0x1FB44))
    last_realtime_room = FrameCount(region6.short(0x1FB46))
    last_door_lag_frames = FrameCount(region6.short(0x1FB10))
    transition_counter = FrameCount(region6.short(0x1FB0E))
    last_lag_counter = FrameCount(region6.short(0x1FB98))

    return State(
        room=room,
        area=area,
        game_state=game_state,
        igt=igt,
        gametime_room=gametime_room,
        last_gametime_room=last_gametime_room,
        realtime_room=realtime_room,
        last_realtime_room=last_realtime_room,
        last_door_lag_frames=last_door_lag_frames,
        transition_counter=transition_counter,
        last_lag_counter=last_lag_counter,
        items=items_string(collected_items_bitmask),
        beams=beams_string(collected_items_bitmask, collected_beams_bitmask))

class RoomTimer(object):
  def __init__(self, rooms, store, timeline):
    self.sock = NetworkCommandSocket()
    self.rooms = rooms
    self.store = store
    self.timeline = timeline
    self.current_room = None
    self.last_room = None
    self.prev_game_state = None
    self.prev_igt = FrameCount(0)
    self.ignore_next_transition = False

  def poll(self):
    state = State.read_from(self.sock, rooms)

    # When the room changes (and we're not in demo mode), we want to
    # take note.  Most of the time, the previous game state was
    # doorTransition, and we'll record the transition below.
    #
    # TODO: if we just started the room timer, or if we just loaded a
    # preset, then we won't know wha the previous room was.  I think
    # that would require changes to the practice ROM.
    if state.game_state == 'normalGameplay' and self.current_room is not state.room:
      if self.current_room is None:
        print("Starting in room %s at %s" % (state.room, state.igt))
        print()
      else:
        print("Transition to %s at %s" % (state.room, state.igt))
      self.last_room = self.current_room
      self.current_room = state.room

    # Check in-game-time to see if we reset state.  This also catches
    # when a preset is loaded, because loading a preset resets IGT to
    # zero.
    if state.igt < self.prev_igt:
      # If we reset state to the middle of a door transition, then we
      # don't want to count the next transition, because it has already
      # been counted.
      print("Reset detected to %s" % state.igt)
      self.timeline.reset(state.igt)
      if state.game_state == 'doorTransition':
        self.ignore_next_transition = True

    if self.prev_game_state == 'doorTransition' and state.game_state == 'normalGameplay':
      if not self.ignore_next_transition:
        self.handle_transition(state)
      self.ignore_next_transition = False

    self.prev_game_state = state.game_state
    self.prev_igt = state.igt

  def handle_transition(self, state):
    if len(self.timeline.transitions) > 0:
      entry_room = self.timeline.transitions[-1][1].room
    else:
      entry_room = NullRoom
    transition_id = TransitionId(
        self.last_room, entry_room, self.current_room,
        state.items, state.beams)
    transition_time = TransitionTime(
        state.last_gametime_room, state.last_realtime_room,
        state.last_lag_counter, state.last_door_lag_frames)
    transition = Transition(transition_id, transition_time)
    self.store.transitioned(transition)
    self.timeline.transitioned(state.igt, transition)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  store = Store(rooms, args.filename)
  timeline = Timeline()
  timer = RoomTimer(rooms, store, timeline)

  while True:
    timer.poll()
    time.sleep(1.0/60)
