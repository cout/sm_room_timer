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

// js: ["new_room_time", {"room": {"room_name": "Wrecked Ship Main Shaft", "entry_room_name": "Basement", "exit_room_name": "Wrecked Ship West Super Room", "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8", "entry_door_id": "a294", "exit_door_id": "a210", "items": "sb.h..m..", "beams": "..C.SIW", "attempts": 1, "time": {"room": {"game": 378, "real": 378, "lag": 0}, "door": {"game": 120, "real": 166, "lag": 46}}, "best_time": {"room": {"game": 378, "real": 378, "lag": 0}, "door": {"game": 0, "real": 46, "lag": 46}}, "mean_time": {"room": {"game": 378, "real": 378, "lag": 0}, "door": {"game": 0, "real": 46, "lag": 46}}, "median_time": {"room": {"game": 378, "real": 378, "lag": 0}, "door": {"game": 0, "real": 46, "lag": 46}}, "p25_time": {"room": {"game": 378.0, "real": 378.0, "lag": 0.0}, "door": {"game": 0.0, "real": 46.0, "lag": 46.0}}, "p75_time": {"room": {"game": 378.0, "real": 378.0, "lag": 0.0}, "door": {"game": 0.0, "real": 46.0, "lag": 46.0}}}, "segment": {"start": {"room_name": "Wrecked Ship Main Shaft", "entry_room_name": "Basement", "exit_room_name": "Wrecked Ship West Super Room", "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8", "entry_door_id": "a294", "exit_door_id": "a210", "items": "sb.h..m..", "beams": "..C.SIW"}, "end": {"room_name": "Wrecked Ship Main Shaft", "entry_room_name": "Basement", "exit_room_name": "Wrecked Ship West Super Room", "room_id": "caf6", "entry_room_id": "cc6f", "exit_room_id": "cda8", "entry_door_id": "a294", "exit_door_id": "a210", "items": "sb.h..m..", "beams": "..C.SIW"}, "time": [378, 378, 0, 46, 166], "median_time": 0, "best_time": 0}, "room_in_segment": {"attempts": 0, "time": 0, "median_time": 0, "best_time": 0}}]

const room_times_columns = [
  { label: "Room", get: o => o.room.room_name },
  { label: "#", get: o => o.room.attempts },
  // { label: "Game", get: o => o.room.time.room.game },
  { label: "Real", get: o => o.room.time.room.real },
  { label: "Lag", get: o => o.room.time.room.lag },
  // { label: "Door Game", get: o => o.room.time.door.game },
  { label: "Door Lag", get: o => o.room.time.door.lag },
  { label: "Door Real", get: o => o.room.time.door.real },
  // { label: "Median Game", get: o => o.room.median_time.room.game },
  { label: "Median Real", get: o => o.room.median_time.room.real },
  { label: "Median Lag", get: o => o.room.median_time.room.lag },
  // { label: "Median Door Game", get: o => o.room.median_time.door.game },
  { label: "Median Door Lag", get: o => o.room.median_time.door.lag },
  { label: "Median Door Real", get: o => o.room.median_time.door.real },
  // { label: "Best Game", get: o => o.room.best_time.room.game },
  { label: "Best Real", get: o => o.room.best_time.room.real },
  { label: "Best Lag", get: o => o.room.best_time.room.lag },
  // { label: "Best Door Game", get: o => o.room.best_time.door.game },
  { label: "Best Door Lag", get: o => o.room.best_time.door.lag },
  { label: "Best Door Real", get: o => o.room.best_time.door.real },
  // { label: "P25 Game", get: o => o.room.p25_time.room.game },
  // { label: "P25 Real", get: o => o.room.p25_time.room.real },
  // { label: "P25 Lag", get: o => o.room.p25_time.room.lag },
  // { label: "P25 Door Game", get: o => o.room.p25_time.door.game },
  // { label: "P25 Door Lag", get: o => o.room.p25_time.door.lag },
  // { label: "P25 Door Real", get: o => o.room.p25_time.door.real },
  // { label: "P75 Game", get: o => o.room.p75_time.room.game },
  // { label: "P75 Real", get: o => o.room.p75_time.room.real },
  // { label: "P75 Lag", get: o => o.room.p75_time.room.lag },
  // { label: "P75 Door Game", get: o => o.room.p75_time.door.game },
  // { label: "P75 Door Lag", get: o => o.room.p75_time.door.lag },
  // { label: "P75 Door Real", get: o => o.room.p75_time.door.real },
];
const room_times_table = new Table(room_times_columns);

document.body.appendChild(room_times_table.elem);

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
    room_times_table.append(data);
  }
});
