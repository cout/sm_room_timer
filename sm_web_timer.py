#!/usr/bin/env python3

from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from route import Route, DummyRoute
from rebuild_history import need_rebuild, rebuild_history
from transition_log import read_transition_log, FileTransitionLog, NullTransitionLog
from history import History
from sm_room_timer import backup_and_rebuild, ThreadedStateReader
from sm_segment_timer import SegmentTimerTerminalFrontend, SegmentTimeTracker, SegmentTimer
from segment import Segment
from transition import TransitionId, TransitionTime
from rooms import Room
from doors import Door
from frame_count import FrameCount
from frame_count_list import FrameCountList
from websocket_server import WebsocketServer

import argparse
import time
import sys
import json
import os

from threading import Thread

# TODO: Don't bother importing these with --headless
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets

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
  # TODO TODO TODO: Figure out how to set doortime_is_real here (it
  # doesn't matter since these values are never written back out to the
  # csv)
  return TransitionTime(
      gametime=func(attempts.gametimes),
      realtime=func(attempts.realtimes),
      roomlag=func(attempts.roomlagtimes),
      door=func(attempts.doortimes),
      realtime_door=func(attempts.doortimes),
      doortime_is_real=True)
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

  def handle_connected(self, session):
    print("connected", session)

  def handle_disconnected(self, session):
    print("disconnected", session)

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
    old_segment_stats = tracker.current_attempt_old_stats
    new_segment_stats = tracker.current_attempt_new_stats
    segment = segment_attempt.segment
    room_in_segment = segment_attempt.transitions[-1]
    old_room_in_segment_stats = old_segment_stats.transition_stats[-1]
    new_room_in_segment_stats = new_segment_stats.transition_stats[-1]

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
        'attempts': new_segment_stats.num_attempts,
        'time': segment_attempt.time.totalrealtime,
        'prev_median_time': old_segment_stats.totalrealtime_p50,
        'prev_best_time': old_segment_stats.totalrealtime_p0,
        'prev_p25_time': old_segment_stats.totalrealtime_p25,
        'prev_p75_time': old_segment_stats.totalrealtime_p75,
      },
      'room_in_segment': {
        'attempts': new_room_in_segment_stats.num_attempts,
        'time': room_in_segment.time.totalrealtime,
        'prev_median_time': old_room_in_segment_stats.totalrealtime_p50,
        'prev_best_time': old_room_in_segment_stats.totalrealtime_p0,
        'prev_p25_time': old_room_in_segment_stats.totalrealtime_p25,
        'prev_p75_time': old_room_in_segment_stats.totalrealtime_p75,
      },
    })

  def new_segment(self, transition):
    self.emit('new_segment', {
      'start': encode_transition_id(transition.id),
    })

class TimerThread(object):
  def __init__(self, history, rooms, doors, transition_log, route,
      json_generator, server, usb2snes):

    self.history = history
    self.transition_log = transition_log
    self.route = route
    self.json_generator = json_generator
    self.server = server

    self.tracker = SegmentTimeTracker(
        history, transition_log, route,
        on_new_room_time=self.json_generator.new_room_time,
        on_new_segment=self.json_generator.new_segment)

    self.state_reader = ThreadedStateReader(
        rooms, doors,
        usb2snes=usb2snes, logger=json_generator)

    self.timer = SegmentTimer(
        self.json_generator, self.state_reader,
        on_transitioned=self.tracker.transitioned,
        on_state_change=self.json_generator.state_changed,
        on_reset=self.tracker.room_reset)

    self.thread = Thread(target=self.run)

  def start(self):
    self.done = False
    self.thread.start()

  def stop(self):
    self.done = True
    self.thread.join()

  def join(self):
    self.thread.join()

  def is_alive(self):
    return self.thread.is_alive()

  def run(self):
    self.state_reader.start()

    try:
      while not self.done and self.state_reader.is_alive() and self.server.is_alive():
        event = self.server.get_event_nowait()
        if event is not None:
          self.handle_server_event(event)
        self.timer.poll()

    finally:
      self.state_reader.stop()

  def handle_server_event(self, event):
    what, *payload = event
    if what == WebsocketServer.CONNECTED:
      self.json_generator.handle_connected(*payload)
    elif what == WebsocketServer.DISCONECTED:
      self.json_generator.handle_disconnected(*payload)

class Browser(object):
  def __init__(self, argv, url):
    self.app = QtWidgets.QApplication(argv)
    self.url = url
    self.window = QtWidgets.QWidget()
    self.layout = QtWidgets.QVBoxLayout()
    self.webview = QtWebEngineWidgets.QWebEngineView()
    self.webview.resize(500, 600)
    self.layout.setContentsMargins(0, 0, 0, 0)
    self.layout.addWidget(self.webview)
    self.window.setLayout(self.layout)

  def run(self):
    self.webview.load(QtCore.QUrl(self.url))
    self.window.show()
    return self.app.exec_()

  def stop(self):
    self.app.quit()

def enable_qt_fractional_scaling():
  # This work with qtwebengine 5.15 to enable fractional scaling (I have
  # the scale factor set to 1.5 in kde plasma settings).  It will not
  # work with qtwebengine 5.14; to get that to work I would need to
  # somehow figure out what the scale factor should be and set
  # QT_SCALE_FACTOR explicitly.
  #
  # Note I am unsure whether QT_ENABLE_HIGHDPI_SCALING uses
  # QT_SCREEN_SCALE_FACTORS (which is what I want) or whether it
  # computes the scale factor automatically based on the dpi.
  del os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']
  os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
  os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'

def run_qt_browser(url):
  enable_qt_fractional_scaling()
  browser = Browser(sys.argv, url)
  sys.exit(browser.run())

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
  parser.add_argument('--headless', action='store_true')
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

    tracker = SegmentTimeTracker(
        history, transition_log, route,
        on_new_room_time=json_generator.new_room_time,
        on_new_segment=json_generator.new_segment)

    timer_thread = TimerThread(history, rooms, doors, transition_log,
        route, json_generator, server, usb2snes=args.usb2snes)
    timer_thread.start()
    shutdown.append(timer_thread.stop)

    if args.headless:
      timer_thread.join()

    else:
      dirname = os.path.dirname(os.path.realpath(__file__))
      filename = 'sm_web_timer.html'
      port = args.port
      url = 'file://%s/%s?port=%s' % (dirname, filename, port)
      run_qt_browser(url)

  finally:
    for f in reversed(shutdown):
      try:
        f()
      except Exception as e:
        print(e)

if __name__ == '__main__':
  main()
