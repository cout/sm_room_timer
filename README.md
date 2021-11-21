Super Metroid Room Timer
========================

This program tracks and provides feedback for individual room times
while playing the [Super Metroid practice hack](https://smpractice.speedga.me/),
version 2.3.1 or later.

<img src="screenshots/sm_room_timer.png?raw=true" alt="Image of room timer in action" width="360">

Usage
-----

For retroarch (must have network commands enabled on port 55354 or
55355):

```
./sm_room_timer.py [-f <filename.csv>]
```

For qusb2snes:

```
./sm_room_timer.py --usb2snes [-f <filename.csv>]
```

Whenever you enter a new room, the script will capture the room time,
door time, and lag time, and optionally record those times in a CSV
file.  It will then print the best times and median times for that room
transition.

Limitations
-----------

Since the room timer is scraping memory, it is not perfectly in sync
with the game, and may occasionally scrape an incorrect time.  If this
happens, the incorrect row can be removed using a text editor or
spreadsheet.

There are mitigations in place to prevent recording an incorrect room
time (for example, the timer will not record a time for a room that was
entered by loading a preset).
