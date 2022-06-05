'use strict';

const get = function(col, obj) {
  try {
    return col.get(obj);
  } catch {
    return "";
  }
};

const fc = function(count) {
  if (count === undefined) {
    return '';
  }

  const sign = count < 0 ? '-' : '';
  count = Math.round(Math.abs(count));
  if (count / 60 < 60) {
    secs = Math.floor(count / 60);
    frames = count % 60;
    return `${sign}${secs}'${frames.toString().padStart(2, '0')}`;
  } else {
    mins = Math.floor(count / 3600);
    secs = Math.floor(count / 60) % 60;
    frames = count % 60;
    return `${sign}${mins}:${secs}'${frames.toString().padStart(2, '0')}`;
  }
};

const fc_delta = function(count, comparison) {
  const delta = comparison == 0 ? -count : count - comparison;
  const pos = delta >= 0 ? '+' : ''
  return `${pos}${fc(delta)}`;
};

const add_classes = function(cell, cls, obj) {
  if (cls) {
    cls.forEach((cls) => {
      cls = (typeof cls === 'function') ? cls(obj) : cls;
      if (cls !== undefined) {
        cell.classList.add(cls);
      }
    });
  }
};

class Widget {
  constructor(elem) {
    this.elem = elem;
  }

  show() {
    this.elem.classList.remove('hidden')
  }

  hide() {
    this.elem.classList.add('hidden')
  }
}

class TableCell extends Widget {
  constructor(data, col) {
    const cell_elem = document.createElement('td');
    super(cell_elem);

    this.data = data;
    this.col = col;

    this.text_elem = document.createTextNode(get(col, data) || '');
    this.elem.appendChild(this.text_elem);
    add_classes(this.elem, col.cls, data);
  }

  update(data) {
    const old_data = this.text_elem.data;
    this.data = data;
    const new_data = get(this.col, data);
    this.text_elem.data = get(this.col, data);
    this.elem.className = "";
    add_classes(this.elem, this.col.cls, data);
  }
};

class TableRow extends Widget {
  constructor(data, columns) {
    const row_elem = document.createElement('tr');
    super(row_elem);

    this.data = { ...data };
    this.columns = columns;
    this.cells = [ ]

    for (const col of this.columns) {
      const cell = new TableCell(data, col);
      this.cells.push(cell);
      this.elem.appendChild(cell.elem);
    }
  }

  update(data) {
    for (const [key, value] of Object.entries(data)) {
      this.data[key] = value;
    }
    for (const cell of this.cells) {
      cell.update(this.data);
    }
  }
}

class Table extends Widget {
  constructor(elem, columns) {
    super(elem);

    this.table_elem = document.createElement('table');

    this.columns = columns

    this.append_header_row();
    this.elem.appendChild(this.table_elem);
  }

  append_header_row() {
    const header_row = document.createElement('thead');

    for (const col of this.columns) {
      const cell = document.createElement('th');
      const text = document.createTextNode(col.label);
      cell.appendChild(text);
      add_classes(cell, col.cls, undefined);
      header_row.appendChild(cell);
    }

    this.table_elem.appendChild(header_row);
  }

  append(data) {
    const row = new TableRow(data, this.columns);
    this.table_elem.appendChild(row.elem);
    row.elem.scrollIntoView();
    return row;
  }

  append_blank_line() {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    const text = document.createTextNode('\u00a0');
    cell.setAttribute('colspan', this.columns.length);
    cell.appendChild(text);
    row.appendChild(cell);
    this.table_elem.appendChild(row)
    row.scrollIntoView();
  }
}

const params = new URLSearchParams(location.search);
const port = params.get('port');
const socket = new WebSocket(`ws://localhost:${port}`)

// js: ["new_room_time", {"room": {
// "room_name": "Wrecked Ship Main Shaft",
// "entry_room_name": "Basement",
// "exit_room_name": "Wrecked Ship West Super Room",
// "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8",
// "entry_door_id": "a294", "exit_door_id": "a210",
// "items": "sb.h..m..", "beams": "..C.SIW",
// "attempts": 1,
// "time": {"room": {"game": 378, "real": 378, "lag": 0},
//          "door": {"game": 120, "real": 166, "lag": 46}},
// "best_time": {"room": {"game": 378, "real": 378, "lag": 0},
//               "door": {"game": 0, "real": 46, "lag": 46}},
// "mean_time": {"room": {"game": 378, "real": 378, "lag": 0},
//               "door": {"game": 0, "real": 46, "lag": 46}},
// "median_time": {"room": {"game": 378, "real": 378, "lag": 0},
//                 "door": {"game": 0, "real": 46, "lag": 46}},
// "p25_time": {"room": {"game": 378.0, "real": 378.0, "lag": 0.0},
//              "door": {"game": 0.0, "real": 46.0, "lag": 46.0}},
// "p75_time": {"room": {"game": 378.0, "real": 378.0, "lag": 0.0},
//              "door": {"game": 0.0, "real": 46.0, "lag": 46.0}}},
// "segment": {
//   "start": {
//     "room_name": "Wrecked Ship Main Shaft",
//     "entry_room_name": "Basement",
//     "exit_room_name": "Wrecked Ship West Super Room",
//     "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8",
//     "entry_door_id": "a294", "exit_door_id": "a210",
//     "items": "sb.h..m..", "beams": "..C.SIW"
//   }, "end": {
//     "room_name": "Wrecked Ship Main Shaft",
//     "entry_room_name": "Basement",
//     "exit_room_name": "Wrecked Ship West Super Room",
//     "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8",
//     "entry_door_id": "a294", "exit_door_id": "a210",
//     "items": "sb.h..m..", "beams": "..C.SIW"
//   },
//   "time": {"room": {"game": 378, "real": 378, "lag": 0},
//            "door": {"game": 120, "real": 166, "lag": 46}},
//   "median_time": 0,
//   "best_time": 0
// },
// "room_in_segment": {"attempts": 0, "time": 0, "median_time": 0, "best_time": 0}}]

const tc = function(o) {
  if (o === undefined) {
    return undefined;
  } if (o.best_time == 0 || o.time <= o.best_time) {
    return 'gold';
  } else if (o.time <= o.p25_time) {
    return 'green';
  } else if (o.time <= o.median_time) {
    return 'lightgreen';
  } else if (o.time <= o.p75_time) {
    return 'lightred';
  } else {
    return 'red';
  }
};

const ssm = function(o) {
  console.error(`  ssm ${JSON.stringify(o)}`);
  if (o === undefined) {
    return undefined;
  } else if (!o.old_segment) {
    return undefined;
  } else if (o.median_time < o.old_segment.median_time) {
    return 'median_time_went_down';
  } else if (o.median_time > o.old_segment.median_time) {
    return 'median_time_went_up';
  }
};

const ssb = function(o) {
  console.error(`  ssb ${JSON.stringify(o)}`);
  if (o === undefined) {
    return undefined;
  } else if (!o.old_segment) {
    return undefined;
  } else if (o.best_time < o.old_segment.best_time) {
    return 'best_time_went_down';
  }
};

const sssob = function(o) {
  console.error(`  ssob ${JSON.stringify(o)}`);
  if (o === undefined) {
    return undefined;
  } else if (!o.old_segment) {
    return undefined;
  } else if (o.sum_of_best_times < o.old_segment.sum_of_best_times) {
    return 'sum_of_best_times_went_down';
  }
};

const room_times_columns = [
  { label: "Room",   get: o => o.room_name,                            },
  { label: "#",      get: o => o.attempts,        cls: [ 'numeric' ]   },
  { label: "Type",   get: o => o.type,            cls: [ 'time-type' ] },
  { label: "Time",   get: o => fc(o.time),        cls: [ 'time', tc ]  },
  { label: "Avg",    get: o => fc(o.avg_time),    cls: [ 'time' ]      },
  { label: "Median", get: o => fc(o.median_time), cls: [ 'time' ]      },
  { label: "Best",   get: o => fc(o.best_time),   cls: [ 'time' ]      },
  // TODO: P25, P75
];
const room_times_table = new Table(
    document.getElementById('room-times'),
    room_times_columns);

const segment_times_columns = [
  { label: "Room",         get: o => o.room_name,                                         },
  { label: "#",            get: o => o.attempts,                      cls: [ 'numeric' ]  },
  { label: "Time",         get: o => fc(o.time),                      cls: [ 'time', tc ] },
  // { label: "Old Median",       get: o => fc(o.median_time),               cls: [ 'time' ]     },
  { label: "\u00b1Median", get: o => fc_delta(o.time, o.median_time), cls: [ 'time' ]     },
  // { label: "Old Best",         get: o => fc(o.best_time),                 cls: [ 'time' ]     },
  { label: "\u00b1Best",   get: o => fc_delta(o.time, o.best_time),   cls: [ 'time' ]     },
];
const segment_times_table = new Table(
    document.getElementById('segment-times'),
    segment_times_columns);

const segment_stats_columns = [
  { label: "Segment",    get: o => o.brief_name,                                              },
  { label: "#",          get: o => o.success_count,                        cls: [ 'numeric' ] },
  { label: "%",          get: o => `${Math.round(o.success_rate * 100)}%`, cls: [ 'numeric' ] },
  { label: "Median",     get: o => fc(o.median_time),                      cls: [ 'time', ssm ]    },
  { label: "\u00b1Best", get: o => fc_delta(o.median_time, o.best_time),   cls: [ 'time', ssb ]    },
  { label: "\u00b1SOB",  get: o => fc_delta(o.median_time, o.sum_of_best_times), cls: [ 'time', sssob ] },
];
const segment_stats_table = new Table(
    document.getElementById('segment-stats'),
    segment_stats_columns);

const gutter = new Widget(document.getElementById("gutter"));

const help_box = new Widget(document.getElementById("help"));

document.addEventListener('keydown', (event) => {
  if (event.key == 'r' || event.key == 'R') {
    console.error('room')
    room_times_table.show()
    segment_times_table.hide()
  } else if (event.key == 's' || event.key == 'S') {
    console.error('segment')
    segment_times_table.show()
    room_times_table.hide()
  } else if (event.key == '?') {
    help_box.show();
  } else if (event.key == ' ') {
    help_box.hide();
  }
});

socket.addEventListener('open', function (event) {
  console.error('open');
});

socket.addEventListener('close', function (event) {
  console.error('close');
});

// Used for segment timer panel
var num_segments = 0;
var current_segment_time_node = undefined;

// Used for segment stats panel
const segment_stats_by_id = { };
const segment_stats_rows_by_id = { };
var last_updated_segment = undefined;
var last_updated_segment_row = undefined;

socket.addEventListener('message', function (event) {
  console.error(event.data);
  const msg = JSON.parse(event.data);
  const type = msg[0];
  const data = msg[1];
  console.error(`${type}: ${data}`);
  if (type == 'new_room_time') {
    help_box.hide();

    room_times_table.append({
      room_name: data.room.room_name,
      attempts: data.room.attempts,
      type: 'Game',
      time: data.room.time.room.game,
      avg_time: data.room.mean_time.room.game,
      median_time: data.room.median_time.room.game,
      best_time: data.room.best_time.room.game,
      p25_time: data.room.p25_time.room.game,
      p75_time: data.room.p75_time.room.game,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Real',
      time: data.room.time.room.real,
      avg_time: data.room.mean_time.room.real,
      median_time: data.room.median_time.room.real,
      best_time: data.room.best_time.room.real,
      p25_time: data.room.p25_time.room.real,
      p75_time: data.room.p75_time.room.real,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Lag',
      time: data.room.time.room.lag,
      avg_time: data.room.mean_time.room.lag,
      median_time: data.room.median_time.room.lag,
      best_time: data.room.best_time.room.lag,
      p25_time: data.room.p25_time.room.lag,
      p75_time: data.room.p75_time.room.lag,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Door Lag',
      time: data.room.time.door.lag,
      avg_time: data.room.mean_time.door.lag,
      median_time: data.room.median_time.door.lag,
      best_time: data.room.best_time.door.lag,
      p25_time: data.room.p25_time.door.lag,
      p75_time: data.room.p75_time.door.lag,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Door Real',
      time: data.room.time.door.real,
      avg_time: data.room.mean_time.door.real,
      median_time: data.room.median_time.door.real,
      best_time: data.room.best_time.door.real,
      p25_time: data.room.p25_time.door.real,
      p75_time: data.room.p75_time.door.real,
    });
    room_times_table.append_blank_line();

    if (current_segment_time_node) {
      // TODO: if Table ever remembers its rows (like Row does with its
      // cells, then this won't work)
      current_segment_time_node.elem.parentNode.removeChild(current_segment_time_node.elem);
    }
    segment_times_table.append({
      room_name: data.room.room_name,
      attempts: data.room_in_segment.attempts,
      time: data.room_in_segment.time,
      median_time: data.room_in_segment.prev_median_time,
      best_time: data.room_in_segment.prev_best_time,
      p25_time: data.room_in_segment.prev_p25_time,
      p75_time: data.room_in_segment.prev_p75_time,
    });
    current_segment_time_node = segment_times_table.append({
      room_name: 'Segment',
      attempts: data.segment.attempts,
      time: data.segment.time,
      median_time: data.segment.prev_median_time,
      best_time: data.segment.prev_best_time,
      p25_time: data.segment.prev_p25_time,
      p75_time: data.segment.prev_p75_time,
    });

  } else if (type == 'new_segment') {
    console.error('new segment')
    if (num_segments > 0) {
      segment_times_table.append_blank_line();
    }
    num_segments += 1;
    current_segment_time_node = undefined;

  } else if (type == 'segment_stats') {
    console.error(data.segments)
    data.segments.forEach((segment) => {
      console.error(segment)
      let row = segment_stats_rows_by_id[segment.id];
      if (row) {
        // Clear out any colors from the last updated row
        if (last_updated_segment_row) {
          last_updated_segment_row.update(last_updated_segment);
        }

        // Update the row for this segment, with colors indicating any
        // improvement
        let old_segment = segment_stats_by_id[segment.id];
        row.update({
          old_segment: old_segment,
          ...segment
        });

        // Save segment stats for next time this row is updated
        segment_stats_by_id[segment.id] = segment;

        // Save last updated segment/row so we can clear colors when the
        // next segment is updated
        last_updated_segment = segment;
        last_updated_segment_row = row;
      } else {
        segment_stats_rows_by_id[segment.id] = segment_stats_table.append(segment)
        segment_stats_by_id[segment.id] = segment;
      }
    });
    segment_stats_table.show();
    gutter.show();
  }
});
