const get = function(col, obj) {
  try {
    return col.get(obj);
  } catch {
    return "";
  }
}

class Table {
  constructor(columns) {
    this.elem = document.createElement('table');
    this.columns = columns

    const header_row = document.createElement('tr');
    for (const col of this.columns) {
      const cell = document.createElement('th');
      const text = document.createTextNode(col.label);
      cell.appendChild(text);
      header_row.appendChild(cell);
    }

    this.elem.appendChild(header_row);
    // this.append({room: { room_name: 'foo' }});
    // this.append({room: { room_name: 'bar' }});
    // this.append({room: { room_name: 'baz' }});

    this.hide();
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
      const text = document.createTextNode(get(col, obj));
      cell.appendChild(text);
      row.appendChild(cell);
    }
    this.elem.appendChild(row);
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
//   "time": [378, 378, 0, 46, 166],
//   "median_time": 0,
//   "best_time": 0
// },
// "room_in_segment": {"attempts": 0, "time": 0, "median_time": 0, "best_time": 0}}]

const room_times_columns = [
  { label: "Room", get: o => o.room_name },
  { label: "#", get: o => o.attempts },
  { label: "Type", get: o => o.type },
  { label: "Time", get: o => o.time },
  { label: "Avg", get: o => o.avg },
  { label: "Median", get: o => o.median },
  { label: "Best", get: o => o.best },
  // { label: "P25", get: o => o.p25 },
  // { label: "P75", get: o => o.p75 },
];
const room_times_table = new Table(room_times_columns);

const segment_times_columns = [
  { label: "Room", get: o => o.room.room_name },
  { label: "#", get: o => o.room_in_segment.attempts },
  { label: "Time", get: o => o.room.time.room.real },
  { label: "\u00b1Median", get: o => TODO },
  { label: "\u00b1Best", get: o => TODO },
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

socket.addEventListener('message', function (event) {
  // console.error(event.data);
  const msg = JSON.parse(event.data);
  const type = msg[0];
  const data = msg[1];
  if (type == 'new_room_time') {
    room_times_table.append({
      room_name: data.room.room_name,
      attempts: data.room.attempts,
      type: 'Game',
      time: data.room.time.room.game,
      avg: data.room.mean_time.room.game,
      median: data.room.median_time.room.game,
      best: data.room.best_time.room.game,
      p25: data.room.p25_time.room.game,
      p75: data.room.p75_time.room.game,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Real',
      time: data.room.time.room.real,
      avg: data.room.mean_time.room.real,
      median: data.room.median_time.room.real,
      best: data.room.best_time.room.real,
      p25: data.room.p25_time.room.real,
      p75: data.room.p75_time.room.real,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Lag',
      time: data.room.time.room.lag,
      avg: data.room.mean_time.room.lag,
      median: data.room.median_time.room.lag,
      best: data.room.best_time.room.lag,
      p25: data.room.p25_time.room.lag,
      p75: data.room.p75_time.room.lag,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Door Lag',
      time: data.room.time.door.lag,
      avg: data.room.mean_time.door.lag,
      median: data.room.median_time.door.lag,
      best: data.room.best_time.door.lag,
      p25: data.room.p25_time.door.lag,
      p75: data.room.p75_time.door.lag,
    });
    room_times_table.append({
      room_name: '',
      attempts: '',
      type: 'Door Real',
      time: data.room.time.door.real,
      avg: data.room.mean_time.door.real,
      median: data.room.median_time.door.real,
      best: data.room.best_time.door.real,
      p25: data.room.p25_time.door.real,
      p75: data.room.p75_time.door.real,
    });

    segment_times_table.append(data);
  }
});
