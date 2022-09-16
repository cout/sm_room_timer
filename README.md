Super Metroid Room Timer
========================

This program tracks and provides feedback for individual room times
while playing the [Super Metroid practice hack](https://smpractice.speedga.me/).

<img src="screenshots/sm_room_timer.png?raw=true" alt="Image of room timer in action" width="360">

Requirements
------------

You must have version 2.4.2 of the Super Metroid practice hack.

The room timer will work with either qusb2snes or retroarch.  If you are
using sd2snes, you will need to use qusb2snes.

Room timer
----------

For retroarch (must have network commands enabled on port 55354 or
55355):

```
./sm_room_timer.py [-f <filename.csv>] [--route]
```

For qusb2snes (required for sd2snes or snes9x-rr):

```
./sm_room_timer.py --usb2snes [-f <filename.csv>] [--route]
```

Whenever you enter a new room, the script will capture the room time,
door time, and lag time, and print them to the screen, along with
relevant statistics.

If a filname is provided (with `-f <filename.csv>`), it will also record
those times to a CSV file, which you can load into the spreadsheet of
your choice.

Segment timer
-------------

To use the segment timer instead of the room timer:

```
./sm_segment_timer.py [--usb2snes] [-f <filename.csv>] [--route]
```

The segment timer will capture times just like the room timer, but
instead of printing statistics for individual rooms, it prints
statistics for segments.

A segment is started when you enter a room after loading state or
loading a preset.  Each room completed after that will be added onto the
segment.  The program remembers uses the room times recorded in the csv
file to compute median and best times for the entire segment.

The time reported by the segment timer is the room's real time plus the
door real time.  This lets you treat segments like splits in LiveSplit,
if you were to split at the door transition.

Summary statistics
------------------

To show summary statistics:

```
./stats.py -f <filename.csv> [--route] [--start="start room"] [--end="end room"]
```

This will show best time, 50/75/90 percentile time, and the difference
between median (P50) and best (P0) time.  The time used is the real time
(game time + lag time) plus the door time for the exit door.  The total
time for all rooms will be shown at the bottom.

Routes
------

You may notice that the total time shown by the stats script doesn't
line up with what you might expect for a full run.  This is because by
default it prints statistics for all the rooms you have practiced.  For
example:

* if you go backward through a door to set up a jump, you might not want
  to count that transition
* if your route picks up an item but you accidentally load a preset
  without that item (e.g. KPDR with spazer)

If you only want to see statistics for rooms/transitions you would use
in a real run, you need to define a route.

To define a route, complete a run from beginning to end.  A route is a
series of transitions starting anywhere and ending at Zebes escape.  It
is okay to load state when defining a route, so long as you do not
deviate from the route until it is complete; duplicate transitions
(same item set and entry/exit door) will be ignored.  When the route is
completed, if you are using the `--route` option, the program will print
"GG" to the console to let you know the route has been completed.

Using the --route flag
----------------------

After defining a route, if you pass the `--route` flag to the stats
script, you will see that it only includes transitions that are part of
the route.

If you use the `--route` flag with the room or segment timer, then once
the route has been defined, any transitions that deviate from the route
will be ignored; only transitions that are part of the route will be
saved to the file.

Segment statistics
------------------

Just like you can print summary statistics for individual room times,
you can also print sumamry statiscics for segments.  To use the segment
statistics script, first define a route (see above), then define a set
of splits.

The easiest way to define a set of splits is to create a splits file.
Each line in the file is the name of a room you want to split on (i.e.
where you want to start a new segment).  If the room occurs more than
once in your route, you can add a number to the end of the room name
(e.g. "Red Tower 3" would be the third trip to red tower in the route).
You can also use "Revisited" as an alias for "2".

For example, in a typical KPDR route, the following splits file:

```
Landing Site
Elevator to Morph Ball Revisited
Flyway
Flyway 2
Big Pink
```

will create these splits:
* Ceres Elevator to Landing Site
* Parlor to Elevator to Morph Ball
* Pit Room to Flyway
* BT to Flyway
* Parlor to Big Pink

Once you have your route and splits defined, you can run the segment
stats script:

```
./segment_stats.py --splits <splits file> -f <filename.csv>
```

The script will then print statistics for each room in each segment,
followed by summary statistics for all the segments at the end.

If you want to watch changes in segment statistics as you play, you can
run the segment stats watcher:

```
./watch_segment_stats.py -f <filename.csv> --splits <splits file>
```

GUI timer (new!)
----------------

A new web-based GUI timer is in development; it combines the room timer,
segment timer, and segment stats watcher into a single application.
First, install the necessary requirements:

```
pip install pyqt5
pip install pyqtwebengine
```

Then, to run it:

```
./sm_web_timer.py [-f <filename.csv>] [--splits <splits file>]
```

As with the room and segment timers, the `-f` and `--splits` options are
optional.

The web-based GUI timer requires Qt and QtWebengine.  If you do not have
Qt and QtWebengine installed, you can still run it in headless mode:

```
./sm_web_timer.py --headless --port 15000 [-f <filename.csv>] [--splits <splits file>]
```

(you may need to comment out the import line for PyQt5 if it fails there)

To view the GUI in your web browser, point it at the following url:

* file:///path/to/sm_web_timer.html?port=15000

The web timer can also be used to report room times in real-time over a
websocket to another process (for example, if you wanted to send updated
times to Funtoon whenever you get a new personal best, this is how you
might do it).  The message format is not documented but is also not
complex; see `sm_web_timer.py` and `sm_web_timer.js` if this is
something you are interested in.

Limitations
-----------

Since the room timer is scraping memory, it is not perfectly in sync
with the game, and may occasionally scrape an incorrect time.  If this
happens, the incorrect row can be removed using a text editor or
spreadsheet.

There are mitigations in place to prevent recording an incorrect room
time (for example, the timer will not record a time for a room that was
entered by loading a preset).

Bugs
----

Occasionally when resetting to the previous room, that room's room times
are assigned to the room that is being reset from.
