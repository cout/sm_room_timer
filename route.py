from doors import NullDoor

def is_ceres_escape(tid):
  return tid.room.name == 'Ceres Elevator' and tid.exit_door.exit_room.name == 'Landing Site'

def is_final_transition(tid):
  return tid.exit_door is NullDoor and tid.room.name == 'Landing Site'

def should_ignore_transition(tid):
  if is_final_transition(tid):
    return False

  return False

def build_route(history):
  route = [ ]
  seen_transitions = { }
  next_room = None
  for tid in history:
    if should_ignore_transition(tid):
      print("IGNORING TRANSITION: %s" % repr(tid))
      continue
    seen = seen_transitions.get(tid)
    if not seen:
      seen_transitions[tid] = True
      if next_room is None or t.room is next_room:
        route.append(tid)
      else:
        print("UNEXPECTED TRANSITION: %s" % repr(tid))
    if is_final_transition(tid):
      break
  return route
