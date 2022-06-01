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

  sign = count < 0 ? '-' : '';
  count = Math.abs(count);
  if (count / 60 < 60) {
    secs = Math.round(count / 60);
    frames = count % 60;
    return `${sign}${secs}'${frames.toString().padStart(2, '0')}`;
  } else {
    mins = Math.round(count / 3600);
    secs = Math.round(count / 60);
    frames = Math.round((count / 60) % 60);
    return `${sign}${mins}${secs}'${frames.toString().padStart(2, '0')}`;
  }
};

class Table {
  constructor(columns) {
    this.elem = document.createElement('table');
    this.columns = columns

    this.append_header_row();
    this.hide();
  }

  append_header_row() {
    const header_row = document.createElement('tr');

    for (const col of this.columns) {
      const cell = document.createElement('th');
      const text = document.createTextNode(col.label);
      cell.appendChild(text);
      header_row.appendChild(cell);
    }

    this.elem.appendChild(header_row);
  }

  show() {
    this.elem.classList.remove('hidden')
  }

  hide() {
    this.elem.classList.add('hidden')
  }

  append(obj) {
    const row = document.createElement('tr');
    for (const col of this.columns) {
      const cell = document.createElement('td');
      const text = document.createTextNode(get(col, obj) || '');
      cell.appendChild(text);
      if (col.css_class) {
        cell.classList.add(col.css_class(obj));
      }
      row.appendChild(cell);
    }
    this.elem.appendChild(row);
    row.scrollIntoView();
  }

  append_blank_line() {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    const text = document.createTextNode('\u00a0');
    cell.setAttribute('colspan', this.columns.length);
    cell.appendChild(text);
    row.appendChild(cell);
    this.elem.appendChild(row)
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

const time_color = function(o) {
  if (o.attempts <= 1 || o.time <= o.best_time) {
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
}

const room_times_columns = [
  { label: "Room", get: o => o.room_name },
  { label: "#", get: o => o.attempts },
  { label: "Type", get: o => o.type },
  { label: "Time", get: o => fc(o.time), css_class: o => time_color(o) },
  { label: "Avg", get: o => fc(o.avg_time) },
  { label: "Median", get: o => fc(o.median_time) },
  { label: "Best", get: o => fc(o.best_time) },
  // { label: "P25", get: o => o.p25_time },
  // { label: "P75", get: o => o.p75_time },
];
const room_times_table = new Table(room_times_columns);

const segment_times_columns = [
  { label: "Room", get: o => o.room_name },
  { label: "#", get: o => o.attempts },
  { label: "Time", get: o => fc(o.time), css_class: o => time_color(o) },
  { label: "\u00b1Median", get: o => fc(o.time - o.median_time) },
  { label: "\u00b1Best", get: o => fc(o.time - o.best_time) },
];
const segment_times_table = new Table(segment_times_columns);

document.body.appendChild(room_times_table.elem);
document.body.appendChild(segment_times_table.elem);

room_times_table.show();

document.addEventListener('keydown', (event) => {
  if (event.key == 'r' || event.key == 'R') {
    console.error('room')
    room_times_table.show()
    segment_times_table.hide()
  } else if (event.key == 's' || event.key == 'S') {
    console.error('segment')
    segment_times_table.show()
    room_times_table.hide()
  }
});

socket.addEventListener('open', function (event) {
  console.error('open');
});

socket.addEventListener('close', function (event) {
  console.error('close');
});

var num_segments = 0;

socket.addEventListener('message', function (event) {
  console.error(event.data);
  const msg = JSON.parse(event.data);
  const type = msg[0];
  const data = msg[1];
  console.error(`${type}: ${data}`);
  if (type == 'new_room_time') {
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

    segment_times_table.append({
      room_name: data.room.room_name,
      ...data.room_in_segment,
    });
  } else if (type == 'new_segment') {
    console.error('new segment')
    if (num_segments > 0) {
      segment_times_table.append_blank_line();
    }
    num_segments += 1;
  }
});
