from doors import NullDoor

def is_ceres_escape(tid):
  return tid.room.name == 'Ceres Elevator' and tid.exit_door.exit_room.name == 'Landing Site'

def is_final_transition(tid):
  return tid.exit_door is NullDoor and tid.room.name == 'Landing Site'

def should_ignore_transition(tid):
  if is_final_transition(tid):
    return False

  return False

class Route(object):
  def __init__(self, ids=None):
    self._ids = ids or [ ]
    self._seen_transitions = { }
    self._next_room = None
    self.complete = False

  def record(self, tid, verbose=True):
    if should_ignore_transition(tid):
      if verbose:
        print("IGNORING TRANSITION: %s" % repr(tid))
      return

    seen = self._seen_transitions.get(tid)
    if not seen:
      self._seen_transitions[tid] = True
      if self._next_room is None or tid.room is self._next_room:
        self._ids.append(tid)
        self._next_room = tid.exit_door.exit_room
      else:
        if verbose:
          print("UNEXPECTED TRANSITION: %s" % repr(tid))

    if is_final_transition(tid):
      self.complete = True

  def find_nth_transition_by_room(self, room, n):
    for tid in self:
      if tid.room == room:
        n -= 1
        if n <= 0:
          return tid

    route = ", ".join(id.room.name for id in self)
    raise RuntimeError("Could not find %s in route: %s" % (room.name, route))

  def __len__(self):
    return len(self._ids)

  def __iter__(self):
    return iter(self._ids)

  def __contains__(self, tid):
    return tid in self._ids

  def __getitem__(self, idx):
    return self._ids[idx]

  def __repr__(self):
    return 'Route(%s)' % repr(self._ids)

class DummyRoute(object):
  def __init__(self):
    self.complete = False

  def __len__(self):
    return 0

  def record(self, tid):
    pass

def build_route(history):
  route = Route()

  for tid in history:
    route.record(tid)
    if route.complete: break

  return route
