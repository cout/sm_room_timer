#!/usr/bin/env python3

from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from route import Route
from rebuild_history import need_rebuild, rebuild_history
from transition_log import read_transition_log, FileTransitionLog, NullTransitionLog
from history import History
from sm_room_timer import backup_and_rebuild, ThreadedStateReader
from sm_segment_timer import SegmentTimerTerminalFrontend, SegmentTimeTracker, SegmentTimer
from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient

from segment import Segment
from transition import TransitionId, TransitionTime
from rooms import Room
from doors import Door
from frame_count import FrameCount
from frame_count_list import FrameCountList

import argparse
import time
import sys
import json
import os
import asyncio
import websockets
from queue import Queue
from threading import Thread

def encode_segment(segment):
  return {
    'name': segment.name,
    'brief_name': segment.brief_name,
    'start': segment.start,
    'end': segment.end,
  }

def encode_transition_id(tid):
  return {
    'room_name': tid.room.name,
    'entry_room_name': tid.entry_room.name,
    'exit_room_name': tid.exit_room.name,
    'room_id': '%04x' % tid.room.room_id,
    'entry_room_id': '%04x' % tid.entry_room.room_id,
    'exit_room_id': '%04x' % tid.exit_room.room_id,
    'entry_door_id': '%04x' % tid.entry_door.door_id,
    'exit_door_id': '%04x' % tid.exit_door.door_id,
    'items': tid.items,
    'beams': tid.beams,
  }

def encode_transition_time(time):
  return {
    'room': {
      'game': time.gametime,
      'real': time.realtime,
      'lag': time.roomlag,
    },
    'door': {
      'game': time.realtime_door - time.door,
      'real': time.realtime_door,
      'lag': time.door,
    },
  }

def encode_room(room):
  return {
    'room_id': '%04x' % room.room_id,
    'name': room.name,
    'brief_name': room.brief_name,
  }

def encode_door(door):
  return {
    'door_id': '%04x' % door.door_id,
    'entry_room_name': door.entry_room.name,
    'exit_room_name': door.exit_room.name,
    'entry_room_id': '%04x' % door.entry_room.room_id,
    'exit_room_id': '%04x' % door.exit_room.room_id,
    'description': door.description,
  }

def encode_frame_count(frame_count):
  return frame_count.count
  # return {
  #   'total_frames': frame_count.count,
  #   'total_seconds': frame_count.to_seconds(),
  # }

encoders = {
  Segment: encode_segment,
  TransitionId: encode_transition_id,
  TransitionTime: encode_transition_time,
  Room: encode_room,
  Door: encode_door,
  FrameCount: encode_frame_count,
}

class JSONEncoder(json.JSONEncoder):
  def default(self, obj):
    cls = type(obj)
    encoder = encoders.get(cls)
    if encoder is not None:
      return encoder(obj)
    else:
      return json.JSONEncoder.default(self, obj)

def apply_to_attempts(attempts, func):
  # TODO TODO TODO: Attempts does not store what we need for "last
  # realtime door" in an easy-to-consume form.
  return TransitionTime(
      func(attempts.gametimes),
      func(attempts.realtimes),
      func(attempts.roomlagtimes),
      func(attempts.doortimes),
      func(attempts.doortimes))
        # state.last_gametime_room, state.last_realtime_room,
        # state.last_room_lag, state.last_door_lag_frames,
        # state.last_realtime_door)

class JsonEventGenerator(object):
  def __init__(self, on_event, debug_log=None, verbose=False):
    self.on_event = on_event
    self.debug_log = debug_log
    self.verbose = verbose

  def emit(self, type, *args):
    s = json.dumps([ type, *args ], cls=JSONEncoder)
    self.on_event(s)

  def log(self, *args):
    self.emit('log', *args)
    self.log_debug(*args)

  def log_debug(self, *args):
    if self.debug_log:
      print(*args, file=self.debug_log)

  def log_verbose(self, *args):
    if self.verbose:
      self.emit('log_verbose', *args)

  def state_changed(self, change):
    l = [ s for s in change.description() ]
    if len(l) > 0: self.emit('state_changed', l)

  def new_room_time(self, transition, attempts, tracker):
    best = apply_to_attempts(attempts, FrameCountList.best)
    mean = apply_to_attempts(attempts, FrameCountList.mean)
    median = apply_to_attempts(attempts, FrameCountList.median)
    p25 = apply_to_attempts(attempts, lambda l: FrameCountList.percentile(l, 25))
    p75 = apply_to_attempts(attempts, lambda l: FrameCountList.percentile(l, 75))

    segment_attempt = tracker.current_attempt
    segment_stats = tracker.current_attempt_stats
    segment = segment_attempt.segment
    room_in_segment_stats = segment_stats.transitions[-1]

    # TODO: I'm too lazy to figure out how to get TransitionTime (which
    # is a NamedTuple) correctly encoded without this hack.
    self.emit('new_room_time', {
      'room': {
        **encode_transition_id(transition.id),
        'attempts': len(attempts),
        'time': encode_transition_time(transition.time),
        'best_time': encode_transition_time(best),
        'mean_time': encode_transition_time(mean),
        'median_time': encode_transition_time(median),
        'p25_time': encode_transition_time(p25),
        'p75_time': encode_transition_time(p75),
      },
      'segment': {
        'start': segment.start,
        'end': segment.end,
        'time': segment_attempt.time,
        'median_time': segment_stats.p50,
        'best_time': segment_stats.p0,
      },
      'room_in_segment': {
        'attempts': room_in_segment_stats.num_attempts,
        'time': room_in_segment_stats.time,
        'median_time': room_in_segment_stats.p50,
        'best_time': room_in_segment_stats.p0,
      },
    })

class WebsocketServer(object):
  def __init__(self, port):
    self.port = port
    self.sockets = set()
    self.loop = None
    self.broadcast_queue = None
    self.thread = Thread(target=self.run)

  def start(self):
    self.loop = None
    self.thread.start()
    while self.loop is None:
      pass

  def stop(self):
    self.loop.call_soon_threadsafe(self.loop.stop())
    self.thread.join()

  def broadcast(self, event):
    def broadcast():
      self.broadcast_queue.put_nowait(event)
    self.loop.call_soon_threadsafe(broadcast)

  def is_alive(self):
    return self.thread.is_alive()

  def run(self):
    self.loop = asyncio.new_event_loop()

    try:
      self.loop.run_until_complete(self.start_server())
      self.loop.run_until_complete(self.run_broadcast_loop())
    finally:
      pass
      # broadcast_task.cancel()

  async def start_server(self):
    self.broadcast_queue = asyncio.Queue()
    await websockets.serve(self.serve, 'localhost', self.port)

  async def run_broadcast_loop(self):
    while True:
      msg = await self.broadcast_queue.get()
      # TODO: a slow socket can slow everyone down
      for sock in self.sockets:
        await sock.send(msg)

  async def serve(self, sock, uri=None):
    self.sockets.add(sock)
    try:
      # async for message in sock:
        # pass
      await sock.wait_closed()
    finally:
      self.sockets.remove(sock)

def main():
  parser = argparse.ArgumentParser(description='SM Room Timer')
  parser.add_argument('-f', '--file', dest='filename', default=None)
  parser.add_argument('--rooms', dest='rooms_filename', default='rooms.json')
  parser.add_argument('--doors', dest='doors_filename', default='doors.json')
  parser.add_argument('--debug', dest='debug', action='store_true')
  parser.add_argument('--debug-log', dest='debug_log_filename')
  parser.add_argument('--verbose', dest='verbose', action='store_true')
  parser.add_argument('--usb2snes', action='store_true')
  parser.add_argument('--route', action='store_true')
  parser.add_argument('--rebuild', action='store_true')
  parser.add_argument('--port', type=int, default=15000)
  # parser.add_argument('--segment', action='append', required=True)
  args = parser.parse_args()

  rooms = Rooms.read(args.rooms_filename)
  doors = Doors.read(args.doors_filename, rooms)
  route = Route() if args.route else DummyRoute()

  if args.filename and need_rebuild(args.filename):
    if not args.rebuild:
      print("File needs to be rebuilt before it can be used; run rebuild_history.py or pass --rebuild to this script.")
      sys.exit(1)

    backup_and_rebuild(rooms, doors, args.filename)

  if args.debug_log_filename:
    debug_log = open(args.debug_log_filename, 'a')
    verbose = True
  elif args.debug:
    debug_log = sys.stdout
    verbose = True
  else:
    debug_log = None
    verbose = args.verbose

  shutdown = [ ]

  try:
    server = WebsocketServer(port=args.port)
    server.start()
    shutdown.append(server.stop)

    json_generator = JsonEventGenerator(
        verbose=verbose, debug_log=debug_log,
        on_event=server.broadcast)

    if args.filename is not None and os.path.exists(args.filename):
      history = read_transition_log(args.filename, rooms, doors)
    else:
      history = History()

    for tid in history:
      route.record(tid)
      if route.complete: break 
    print('Route is %s' % ('complete' if route.complete else 'incomplete'))

    transition_log = FileTransitionLog(args.filename) if args.filename is not None else NullTransitionLog()

    if args.usb2snes:
      sock = WebsocketClient('sm_room_timer', logger=json_generator)
    else:
      sock = NetworkCommandSocket()

    tracker = SegmentTimeTracker(
        history, transition_log, route,
        on_new_room_time=json_generator.new_room_time)

    state_reader = ThreadedStateReader(rooms, doors, sock)
    state_reader.start()
    shutdown.append(state_reader.stop)

    timer = SegmentTimer(
        json_generator, state_reader,
        on_transitioned=tracker.transitioned,
        on_state_change=json_generator.state_changed,
        on_reset=tracker.room_reset)

    while state_reader.is_alive() and server.is_alive(): timer.poll()

  finally:
    for f in shutdown:
      try:
        f()
      except Exception as e:
        print(e)

if __name__ == '__main__':
  main()
