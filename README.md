Super Metroid Room Timer
========================

This program tracks and provides feedback for individual room times
while playing the [Super Metroid practice hack](https://smpractice.speedga.me/).

<img src="screenshots/sm_room_timer.png?raw=true" alt="Image of room timer in action" width="360">

Usage
-----

For retroarch (must have network commands enabled on port 55354 or
55355):

```
./sm_room_timer.py [-f <filename.csv>] [--route]
```

For qusb2snes:

```
./sm_room_timer.py --usb2snes [-f <filename.csv>] [--route]
```

Whenever you enter a new room, the script will capture the room time,
door time, and lag time, and optionally record those times in a CSV
file.  It will then print the best times and median times for that room
transition.

Routes
------

The `--route` option may be used to ensure that only transitions in the
route are processed.  For example:
* if you go backward through a door to set up a jump, you might not want
  to count that transition
* if your route picks up an item but you accidentally load a preset
  without that item (e.g. KPDR with spazer)

To define a route, complete a run from beginning to end.  A route is a
series of transitions starting anywhere and ending at Ceres escape.  It
is okay to load state when defining a route, so long as you do not
deviate from the route until it is complete; duplicate transitions
(same item set and entry/exit door) will be ignored.  When the route is
completed, if you are using the `--route` option, the program will print
"GG" to the console to let you know the route has been completed.

Summary statistics
------------------

To show summary statistics:

```
./stats.py -f <filename.csv> [--route] [--start] [--end]
```

This will show best time, 50/75/90 percentile time, and the difference
between median (P50) and best (P0) time.  The time used is the real time
(game time + lag time) plus the door time for the exit door.  The total
time for all rooms will be shown at the bottom.

When the `--route` option is used, only transitions in the route are
used; transitions that are stored in the file but are not in the route
are excluded.

If you only want to show a subset of transitions in the route (e.g. from
Botwoon to Draygon), use `--start` and `--end` to specify the start and
end room names.

Limitations
-----------

Since the room timer is scraping memory, it is not perfectly in sync
with the game, and may occasionally scrape an incorrect time.  If this
happens, the incorrect row can be removed using a text editor or
spreadsheet.

There are mitigations in place to prevent recording an incorrect room
time (for example, the timer will not record a time for a room that was
entered by loading a preset).
