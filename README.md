Super Metroid Room Timer
========================

This is a quick and dirty way to record room times while playing the
[Super Metroid practice hack](https://smpractice.speedga.me/).

Usage
-----

1. Start retroarch and enable network commands on port 55354 or 55355.

2. Run the timer:

```
./sm_room_timer.py [-f <filename.csv>]
```

Whenever you enter a new room, the script will capture the room time,
door time, and lag time, and optionally record those times in a CSV
file.  It will then print the best times and median times for that room
transition.

Limitations
-----------

* The script only uses the previous and current room to identify a
  transition, which can be a problem for some routes.

* Rooms not defined in `rooms.json` will show up as a hex number.

