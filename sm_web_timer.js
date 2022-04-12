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
  }

  append(obj) {
    const row = document.createElement('tr');
    for (const col of this.columns) {
      const cell = document.createElement('td');
      const text = document.createTextNode(col.get(obj));
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
  { label: "Game Time", get: o => o.room.time.room.game },
  { label: "Real Time", get: o => o.room.time.room.real },
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
