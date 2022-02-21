#!/usr/bin/env python3

from sm_room_timer import Store, RoomTimer, TerminalFrontend, backup_and_rebuild
from rooms import Rooms, NullRoom
from doors import Doors, NullDoor
from route import Route
from rebuild_history import need_rebuild, rebuild_history
from retroarch.network_command_socket import NetworkCommandSocket
from qusb2snes.websocket_client import WebsocketClient

import argparse
import itertools
import time

class Segment(object):
  def __init__(self, start=None, end=None):
    self.start = start
    self.end = end

  def __repr__(self):
    return "Segment(%s, %s)" % (self.start, self.end)

  def extend_to(self, tid):
    if self.start is None: self.start = tid
    self.end = tid

class SegmentAttempt(object):
  def __init__(self):
    pass

  def append(self, transition):
    pass

class SegmentStore(Store):
  def __init__(self, rooms, doors, route, filename=None):
    Store.__init__(self, rooms, doors, route, filename=filename)

    self.current_segment = Segment()
    self.route_iter = None

  def transitioned(self, transition):
    ret = Store.transitioned(self, transition)

    # TODO:
    # * For the first version, whenever a transition is completed, we
    #   can brute force search the history for that segment and compute
    #   the median times on the fly, rather than keeping running totals.
    # * As an optimization, we can store a mapping of transition id to
    #   segment attempts so we don't have to iterate over the entire
    #   history each time.  A SegmentAttempt would be mapped from each
    #   transition id in the segment.
    # * We also need to know whether to extend the segment.  For this we
    #   need to know if the transition is the next transition in the
    #   route.  Use external iterator for this.

    if self.route_iter is None:
      next_tid = None
      new_segment = True
    else:
      next_tid = next(self.route_iter, None)
      new_segment = next_tid != transition.id

    print("New segment: %s" % new_segment)
    print("TID: %s" % transition.id)
    print("Next TID: %s" % next_tid)

    if new_segment:
      # This is the first transition in a segment
      self.route_iter = itertools.dropwhile(
          lambda tid: transition.id != tid,
          self.route)
      next(self.route_iter)
      self.current_segment = Segment(start=transition.id, end=transition.id)
    else:
      # This is a continuation of the current segment
      self.current_segment.extend_to(transition.id)

    print("Current segment: %s" % self.current_segment)
    print("")

    return ret

class SegmentTimer(RoomTimer):
  def __init__(self, rooms, doors, store, sock, debug_log=None, verbose=False):
    RoomTimer.__init__(self, rooms, doors, store, sock, debug_log, verbose)

class SegmentTimerTerminalFrontend(TerminalFrontend):
  def __init__(self, debug_log=None, verbose=False):
    TerminalFrontend.__init__(self, debug_log=debug_log, verbose=verbose)

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

  store = SegmentStore(rooms, doors, route, args.filename)

  if args.usb2snes:
    sock = WebsocketClient('sm_room_timer')
  else:
    sock = NetworkCommandSocket()

  if args.debug_log_filename:
    debug_log = open(args.debug_log_filename, 'a')
    verbose = True
  elif args.debug:
    debug_log = sys.stdout
    verbose = True
  else:
    debug_log = None
    verbose = args.verbose

  frontend = SegmentTimerTerminalFrontend(verbose=verbose, debug_log=debug_log)
  timer = SegmentTimer(frontend, rooms, doors, store, sock)

  while True:
    timer.poll()
    time.sleep(1.0/60)

if __name__ == '__main__':
  main()
