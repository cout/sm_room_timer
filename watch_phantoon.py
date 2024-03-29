#!/usr/bin/env python3

import os
import sys

from retroarch.network_command_socket import NetworkCommandSocket
from state import State
from rooms import Rooms
from doors import Doors
from memory import SparseMemory

import argparse
import time
import sys

WRAM_START = 0x7EFD00 - 0x7E0000

def format_time(frames):
  return "%s'%02d" % (frames // 60, frames % 60)

class PhantoonState(object):
  def __init__(self, **attrs):
    for name in attrs:
      setattr(self, name, attrs[name])

  def __repr__(self):
    return "PhantoonState(%s)" % ', '.join([ '%s=%s' % (k,repr(v)) for k,v in
      self.__dict__.items() ])

  @staticmethod
  def read_from(sock):
    addresses = (
        (0x09c6, 0x0e),      # 0x9c6 to 0x9d3
        (0x0f7a, 0x74),      # 0xf7a to 0xfef
        (0x102a, 0x2),
        (0x1988, 0x2),
        (WRAM_START, 0x5a), # 0xfd00 to 0xfd59
        )

    mem = SparseMemory.read_from(sock, *addresses)

    if mem is None: return None

    volley_damage = mem.short(0x102a)
    timer = mem.short(0x0fb0)
    state = mem.short(0x0fb2)
    pattern_timer = mem.short(0x0fe8)
    # movement_index = mem.short(0x0fa8)
    # movement_speed = mem.short(0x0faa)
    # speed_ramp_cycle_phase = mem.short(0x0fae)
    invisible = mem[0x0fb6]
    round_one_side = mem[0x0fec]
    something_bitmask = mem.short(0x1988)
    x_pos = mem.short(0x0f7a)
    y_pos = mem.short(0x0f7a)
    hit_points = mem.short(0x0f8c)

    missiles = mem.short(0x09c6)
    selected_item = mem.short(0x09d2)
    realtime_room = mem.short(WRAM_START + 0x6)
    shot_timer = mem.short(WRAM_START + 0x58)

    return PhantoonState(
        volley_damage=volley_damage,
        timer=timer,
        state=state,
        pattern_timer=pattern_timer,
        # movement_index=movement_index,
        # movement_speed=movement_speed,
        # speed_ramp_cycle_phase=speed_ramp_cycle_phase,
        invisible=invisible,
        round_one_side=round_one_side,
        eye_open=((something_bitmask & 0x4000) != 0),
        x_pos=x_pos,
        y_pos=y_pos,
        hit_points=hit_points,
        missiles=missiles,
        selected_item=selected_item,
        shot_timer=shot_timer,
        realtime_room=realtime_room,
        )

class PhantoonRound(object):
  def __init__(self, round_num, sub_round_num, state):
    self.round_num = round_num
    self.sub_round_num = sub_round_num

    if sub_round_num == 0:
      self.round_id = round_num
    else:
      self.round_id = '%d.%d' % (round_num, sub_round_num)

    self.side = self._side_from_state(state)
    self.speed = self._speed_from_state(state)
    self.eye_close_speed = None

  def _side_from_state(self, state):
    if self.round_num == 1 and self.sub_round_num == 0:
      return 'RIGHT' if state.round_one_side == 0 else 'LEFT'
    else:
      return 'RIGHT' if state.x_pos > 128 else 'LEFT'

  def _speed_from_state(self, state):
    if state.pattern_timer > 360:
      return 'SLOW'
    elif state.pattern_timer > 60:
      return 'MID'
    else:
      return 'FAST'

  def eye_opened(self, state):
    if state.timer > 30:
      self.eye_close_speed = 'SLOW'
    elif state.timer > 15:
      self.eye_close_speed = 'MID'
    else:
      self.eye_close_speed = 'FAST'

class PhantoonFight(object):
  def __init__(self):
    self.round_num = 0
    self.sub_round_num = 0
    self.round = None

    self.round_count = 0
    self.sub_round_count = 0

    self.missed_eye_close = None
    self.volleys = [ ]
    self.doppler_timings = [ ]
    self.doppler_hit_times = [ ]
    self.doppler_hit_timings = [ ]

    self.eye_open_speeds = [ ]
    self.eye_close_speeds = [ ]

    self.fight_time = None

  def new_round(self, state):
    self.round_num += 1
    self.sub_round_num = 0
    self.round = PhantoonRound(self.round_num, self.sub_round_num, state)
    self.round_count += 1
    self.missed_eye_close = False
    self._new_round_or_sub_round(state)

  def new_sub_round(self, state):
    self.sub_round_num += 1
    self.round = PhantoonRound(self.round_num, self.sub_round_num, state)
    self.sub_round_count += 1
    self.missed_eye_close = True
    self._new_round_or_sub_round(state)

  def _new_round_or_sub_round(self, state):
    self.volleys = [ ]
    self.doppler_timings = [ ]
    self.doppler_hit_times = [ ]
    self.doppler_hit_timings = [ ]
    self.round_start_hit_points = state.hit_points

  def eye_opened(self, state):
    if self.round is None: return

    self.round.eye_opened(state)

  def volley_ended(self, volley_damage):
    self.volleys.append(volley_damage)

  def shot_doppler(self, shot_timer):
    self.doppler_timings.append(shot_timer)

  def doppler_hit(self, realtime_room):
    if len(self.doppler_hit_times) > 0:
      hit_timing = realtime_room - self.doppler_hit_times[-1]
      self.doppler_hit_timings.append(hit_timing)
    self.doppler_hit_times.append(realtime_room)

  def round_ended(self, state):
    if self.round is None: return

    if self.sub_round_num == 0:
      self.eye_open_speeds.append(self.round.speed)
    else:
      self.eye_open_speeds[-1] += ("+%s" % self.round.speed.lower())

    if self.round.eye_close_speed is not None:
      if self.missed_eye_close:
        self.eye_close_speeds.append(self.round.eye_close_speed + ' (missed)')
      else:
        self.eye_close_speeds.append(self.round.eye_close_speed)

    self.last_round_damage = self.round_start_hit_points - state.hit_points

  def fight_ended(self, state):
    self.fight_time = state.realtime_room + 726 # 1024 if called from state d948

  def is_fight_over(self, state):
    return self.round_num > 0 and state.state in (
      # 0xd948,
      0xd98b,
      0xda51,
      0xda86,
      0xdad7,
      0xdb3d,
      )

  def round_summary(self):
    if self.round is None: return

    l = [ ]

    if self.round.eye_close_speed is not None:
      l.append('ROUND %s was a %s %s (eye close %s)' % (self.round.round_id,
        self.round.side, self.round.speed, self.round.eye_close_speed))
    else:
      l.append('ROUND %s was a %s %s' % (self.round.round_id,
        self.round.side, self.round.speed))

    if self.last_round_damage > 0:
      volleys = [ str(volley) for volley in self.volleys ]
      volley_damage = '(%s)' % (', '.join(volleys))

      dopplers = [ str(t) for t in self.doppler_timings ]
      dopplers_hit = [ str(t) for t in self.doppler_hit_timings ]

      l.append('ROUND %s DAMAGE %s %s ' % (self.round.round_id,
        self.last_round_damage, volley_damage))
      l.append('  DOPPLERS: %s' % ', '.join(dopplers))
      l.append('  DOPPLERS HIT: %s' % ', '.join(dopplers_hit))

    return l

  def summary(self):
      rounds = '%s' % self.round_count
      if self.sub_round_count > 0:
        rounds += ('+%s' % self.sub_round_count)

      fight_time = format_time(self.fight_time)
      eye_open_speeds = ', '.join(self.eye_open_speeds)
      eye_close_speeds = ', '.join(self.eye_close_speeds)

      return (
        'Phantoon was defeated in %s rounds in %s' % (rounds, fight_time),
        'Eye open speeds were: %s' % eye_open_speeds,
        'Eye close speeds were: %s' % eye_close_speeds,
      )

class PhantoonWatcher(object):
  def __init__(self, sock):
    self.sock = sock

    self.prev_state = None
    self.reset()

  def reset(self):
    self.fight = PhantoonFight()
    self.in_dopplers = False
    self.reported_fight_summary = False
    self.last_transition_time = None

  def round_ended(self, state):
    # if this is the first round, then there is no round to end
    if self.fight.round is None: return

    self.fight.round_ended(state)
    self.report_previous_round(state)
    self.report_phantoon_hit_points(state)

    self.in_dopplers = False

  def report_phantoon_hit_points(self, state):
    if state.hit_points == 0:
      print()
      print('PHANTOON HAS LEFT THE SHIP')
      pass

    elif self.fight.last_round_damage > 0:
      print(state.hit_points, 'HIT POINTS REMAIN')

  def report_previous_round(self, state):
    if self.fight.sub_round_num == 0:
      print()

    if self.fight.round is not None:
      for line in self.fight.round_summary():
        print(line)

  def report_fight_summary(self):
      print()
      print('Fight summary:')
      for line in self.fight.summary():
        print('  %s' % line)

  # TODO TODO TODO
  #
  # Read 102A (damage dealt this set)

  def is_reset(self, state):
    if self.prev_state is None:
      return True

    if state.hit_points > self.prev_state.hit_points:
      return True

    if state.realtime_room < self.prev_state.realtime_room:
      return True

    return False

  def poll(self):
    state = PhantoonState.read_from(sock)

    if state is None: return

    if self.prev_state is None or state.state != self.prev_state.state:
      if self.last_transition_time is not None:
        s = '(%s)' % (state.realtime_room - self.last_transition_time)
      else:
        s = ''
      # print('New state: 0x%x %s' % (state.state, s))
      self.last_transition_time = state.realtime_room

    # if self.prev_state is None or state.selected_item != self.prev_state.selected_item:
      # print('Selected item is now:', state.selected_item)

    if self.is_reset(state):
      self.reset()

    if self.fight.is_fight_over(state) and not self.reported_fight_summary:
      self.fight.fight_ended(state)
      self.report_fight_summary()
      self.reported_fight_summary = True

    # d408 - initial fireball spin
    if self.prev_state is not None and self.prev_state.state == 0xd508 and state.state != 0xd508:
      print()
      print('Round one, fight!')

    # d5e7 - first half of a round (phantoon invisible)
    if self.prev_state is not None and self.prev_state.state != 0xd5e7 and state.state == 0xd5e7:
      self.round_ended(state)
      self.fight.new_round(state)

    # d82a - second half of a round (phantoon visible)
    if self.prev_state is not None and self.prev_state.state != 0xd82a and state.state == 0xd82a:
      self.round_ended(state)
      self.fight.new_sub_round(state)

    # round ended due to phantoon death (no hit points remaining)
    if self.prev_state is not None and state.hit_points == 0 and self.prev_state.hit_points > 0:
      self.round_ended(state)

    if self.prev_state is not None and self.prev_state.volley_damage != state.volley_damage:
      if state.volley_damage == 0:
        self.fight.volley_ended(self.prev_state.volley_damage)

    # d60d - phantoon's eye is open
    if state.state == 0xd60d and self.prev_state.state != 0xd60d:
      self.fight.eye_opened(state)

    # d678 - phantoon is swooping
    if state.state == 0xd678:
      if not self.in_dopplers:
        self.in_dopplers = True

      # TODO - The shot timer is only incremented if the infohud is set
      # to shot timer mode
      if self.prev_state is not None and \
        state.shot_timer < self.prev_state.shot_timer and \
        state.selected_item == 1:
        self.fight.shot_doppler(self.prev_state.shot_timer)

      # TODO:
      # 1. This assumes the hit points were reduced from a doppler, but
      #    it could have been a missile or a charge shot (probably
      #    impossible to know just from scraping memory)
      # 2. The two initial missile volleys are also counted as dopplers,
      #    but they probably should not be.  Phantoon's state is the
      #    same in both cases, but iirc there is another variable that
      #    controls phantoon's movement in the swoop.
      # - ideally we would count the number of volleys, but we currently
      #   count volleys based on when the volley damage value goes to 0.
      #   As a result, the second and third volleys get lumped together
      #   into a single volley (which is how the boss logic works, but
      #   not how most players think about it).
      if state.hit_points != self.prev_state.hit_points:
        self.fight.doppler_hit(state.realtime_room)

    self.prev_state = state

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Watch phantoon')
  args = parser.parse_args()

  sock = NetworkCommandSocket()
  watcher = PhantoonWatcher(sock)

  print()
  print('GRAB SOME POPCORN, THIS IS GOING TO BE A GOOD FIGHT!')
  print()

  while True:
    watcher.poll()
