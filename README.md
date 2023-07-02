Super Metroid Room Timer
========================

This program tracks and provides feedback for individual room times
while playing the [Super Metroid practice hack](https://smpractice.speedga.me/).

<img src="screenshots/sm_practice_timer.png?raw=true" alt="Image of practice timer in action" width="360">

Requirements
------------

You must have python installed to use the timer (I use python 3.8.5, but
it should work with newer versions too; if it does not, please file a
bug report).

You must have version 2.4.2 or 2.5.0 of the Super Metroid practice hack.

The room timer will work with either qusb2snes or retroarch.  If you are
using sd2snes, you will need to use qusb2snes.

To install the requirements, run:

```
pip install -r requirements.txt
```

If you are only using the text-based timers that run in a terminal
(`sm_room_timer.py` and `sm_segment_timer.py`), install requirements
from `base-requirements.txt` instead.

Running the timer
-----------------

To run the practice timer:

```
./sm_practice_timer.py [-f <filename.csv>] [--splits <splits file>] [--usb2snes or --retroarch]
```

If using qusb2snes, use `--usb2snes`.

if using retroarch, use `--retroarch` and enable network commands on
port 55354 or 55355.

Timing rooms
------------

Whenever you enter a new room, the script will capture the room time,
door time, and lag time, and print them to the screen, along with
relevant statistics.

To save the room times in a CSV file, add `-f <filename.csv>` to the
command you used to run the timer.

Timing segments
---------------

By default the timer is in room time mode.  To switch to segment time
mode, press S.

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

Room/segment history
--------------------

To see the history for a room or segment, click on its name.  You should
see a window with all the times for that room listed.  Keep in mind that
the timer differentiates between different entry/exit doors and
different equipment, because sometimes the same room is visited multiple
times during a run, with different strats depending on the items Samus
has collected.

The window also shows two graphs.  On the left is a graph of the room or
segment times over time.  On the right is a histogram.

Segment splits
--------------

The timer can also give show statistics for segments of a run.

To do so, you must first define a route.  To define a route, complete a
run from beginning to end.  When the route is completed, the program
will print "GG" to the terminal to let you know the route has been
completed. (TODO - there is currently no indication in the GUI when the
route is complete; you have to look at the terminal where you ran the
timer).

Once you have a route, you need to define splits.

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

Some sample splits are provided under the `splits/` directory.

Once you have a route and a splits file, re-run the timer with the
`--splits` option.  You should see summary statistics (median time, best
time, sum of best rooms) for each segment of the run and statistics for
the whole run (sum of median, sum of best, sum of best rooms).

Headless mode
-------------

The GUI timer requires Qt and QtWebengine.  If you do not have Qt and
QtWebengine installed, you can run in headless mode:

```
./sm_practice_timer.py --headless --port 15000 [-f <filename.csv>] [--splits <splits file>] [--usb2snes or --retroarch]
```

(you may need to comment out the import line for PyQt5 if it fails there)

To view the GUI in your web browser, point it at the following url:

* file:///path/to/sm_web_timer.html?port=15000

The timer can also be used to report room times in real-time over a
websocket to another process (for example, if you wanted to send updated
times to Funtoon whenever you get a new personal best, this is how you
might do it).  The message format is not documented but is also not
complex; see `sm_practice_timer.py` and `sm_practice_timer.js` if this
is something you are interested in.

Running the text-based timers
-----------------------------

If you don't want to use the GUI, you can run the room and segment
timers in a terminal window.

To run the room timer:

```
./sm_room_timer.py [-f <filename.csv>] [--route] [--usb2snes or --retroarch]
```

To run the segment timer:

```
./sm_segment_timer.py [--usb2snes] [-f <filename.csv>] [--route] [--usb2snes or --retroarch]
```

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

Sometimes (when using SD2SNES) the timer may miss a room during the
initial run to create a route.  If this happens you will not have a
complete route.  The only fix is to start over or manually edit the CSV
file.
