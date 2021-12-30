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
    self.ids = ids or [ ]
    self.seen_transitions = { }
    self.next_room = None
    self.complete = False

  def append(self, tid):
    if should_ignore_transition(tid):
      print("IGNORING TRANSITION: %s" % repr(tid))
      return

    seen = self.seen_transitions.get(tid)
    if not seen:
      self.seen_transitions[tid] = True
      if self.next_room is None or t.room is self.next_room:
        self.ids.append(tid)
      else:
        print("UNEXPECTED TRANSITION: %s" % repr(tid))

    if is_final_transition(tid):
      self.complete = True

  def __len__(self):
    return len(self.ids)

  def __iter__(self):
    return iter(self.ids)

  def __repr__(self):
    return 'Route(%s)' % repr(self.ids)

def build_route(history):
  route = Route()

  for tid in history:
    route.append(tid)
    if route.complete: break

  return route
