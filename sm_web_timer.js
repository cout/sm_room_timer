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
    const secs = Math.floor(count / 60);
    const frames = count % 60;
    return `${sign}${secs}'${frames.toString().padStart(2, '0')}`;
  } else {
    const mins = Math.floor(count / 3600);
    const secs = Math.floor(count / 60) % 60;
    const frames = count % 60;
    return `${sign}${mins}:${secs.toString().padStart(2, '0')}'${frames.toString().padStart(2, '0')}`;
  }
};

const fc_delta = function(count, comparison) {
  const delta = comparison == 0 ? -count : count - comparison;
  const pos = delta >= 0 ? '+' : ''
  return `${pos}${fc(delta)}`;
};

const pct = function(rate) {
  if (rate === undefined) {
    return undefined;
  }
  return `${Math.round(rate * 100)}%`;
};

const ts_format = new Intl.DateTimeFormat([], { dateStyle: 'short', timeStyle: 'short' });

const ts = function(timestamp) {
  return ts_format.format(Date.parse(timestamp));
};

const add_classes = function(elem, classes, obj) {
  if (classes) {
    classes.forEach((cls) => {
      cls = (typeof cls === 'function') ? cls(obj) : cls;
      if (cls !== undefined) {
        elem.classList.add(cls);
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

  clear() {
    this.elem.innerHTML = '';
  }
}

class TableCell extends Widget {
  constructor(data, col) {
    super(document.createElement('td'));

    this.col = col;

    this.update(data);
  }

  update(data) {
    this.data = data;

    this.clear();

    const text = String(get(this.col, data) || '');
    const lines = text.split('\n');
    for (const line of lines) {
      const div = document.createElement('div')
      // div.appendChild(document.createTextNode(line));
      div.innerHTML = line // TODO: line might not be sanitized!
      add_classes(div, this.col.cls, data);
      this.elem.appendChild(div)
    }
    if (this.col.onclick) {
      this.elem.onclick = evt => this.col.onclick(data);
    } else {
      this.elem.onclick = undefined;
    }
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

class TableRows extends Widget {
  constructor(elem, columns) {
    super(elem);

    this.columns = columns;
  }

  append_row(data) {
    const row = new TableRow(data, this.columns);
    this.elem.appendChild(row.elem);
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
    this.elem.appendChild(row)
    row.scrollIntoView();
  }
}

class Table extends Widget {
  constructor(columns) {
    super(document.createElement('table'));

    this.columns = columns;

    this.append_group_row();
    this.append_header_row();
  }

  append_group_row() {
    const groups = [ ];
    var current_group = { label: undefined, colspan: 0, dummy_group: true };
    for (const col of this.columns) {
      if (col.group !== current_group.label) {
        groups.push(current_group);
        current_group = { label: col.group, colspan: 1 };
      } else {
        current_group.colspan += 1;
      }
    }
    groups.push(current_group);

    if (!current_group.dummy_group) {
      const group_row = document.createElement('tr');

      for (const group of groups) {
        const cell = document.createElement('th');
        cell.setAttribute('colspan', group.colspan);
        if (group.label !== undefined) {
          const div = document.createElement('div');
          const text = document.createTextNode(group.label);
          div.classList.add('group');
          div.appendChild(text);
          cell.appendChild(div);
        }
        group_row.appendChild(cell);
      }

      if (!this.header) {
        this.header = new TableRows(document.createElement('thead'));
        this.elem.appendChild(this.header.elem);
      }

      this.header.elem.appendChild(group_row);
    }
  }

  append_header_row() {
    const header_row = document.createElement('tr');

    for (const col of this.columns) {
      const cell = document.createElement('th');
      const div = document.createElement('div')
      const text = document.createTextNode(col.label);
      div.appendChild(text);
      add_classes(div, col.cls, undefined);
      cell.appendChild(div);
      header_row.appendChild(cell);
    }

    if (!this.header) {
      this.header = new TableRows(document.createElement('thead'));
      this.elem.appendChild(this.header.elem);
    }

    this.header.elem.appendChild(header_row);
  }

  append_row(data) {
    if (!this.body) {
      this.body = new TableRows(document.createElement('tbody'), this.columns);
      this.elem.appendChild(this.body.elem);
    }

    return this.body.append_row(data);
  }

  append_blank_line() {
    if (!this.body) {
      this.body = new TableRows(document.createElement('tbody'), this.columns);
      this.elem.appendChild(this.body.elem);
    }

    return this.body.append_blank_line();
  }

  clear_footer() {
    if (this.footer) {
      this.footer.clear();
    }
  }

  append_footer_row(data, cols) {
    cols = cols || this.columns;
    const row = new TableRow(data, cols);

    if (!this.footer) {
      this.footer = new TableRows(document.createElement('tfoot'));
      this.elem.appendChild(this.footer.elem);
    }

    this.footer.elem.appendChild(row.elem);
  }
}

class Chart extends Widget {
  create_plot() {
    const plot = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    plot.classList.add('plot');
    return plot;
  }

  draw_axes(xlim, ylim) {
    const axes = document.createElementNS("http://www.w3.org/2000/svg", "g");
    axes.classList.add('axes');

    const range = (lim) => lim[1] == lim[0] ? 1 : lim[1] - lim[0];
    const t = (v, lim) => (v - lim[0]) / range(lim);

    const xaxis = document.createElementNS("http://www.w3.org/2000/svg", "line");
    xaxis.classList.add('axis');
    xaxis.setAttribute('x1', `${100 * t(xlim[0], xlim)}%`);
    xaxis.setAttribute('y1', `${100 * t(0,       ylim)}%`);
    xaxis.setAttribute('x2', `${100 * t(xlim[1], xlim)}%`);
    xaxis.setAttribute('y2', `${100 * t(0,       ylim)}%`);
    axes.appendChild(xaxis);

    const yaxis = document.createElementNS("http://www.w3.org/2000/svg", "line");
    yaxis.classList.add('axis');
    yaxis.setAttribute('x1', `${100 * t(0,       xlim)}%`);
    yaxis.setAttribute('y1', `${100 * t(ylim[0], ylim)}%`);
    yaxis.setAttribute('x2', `${100 * t(0,       xlim)}%`);
    yaxis.setAttribute('y2', `${100 * t(ylim[1], ylim)}%`);
    axes.appendChild(yaxis);

    return axes;
  }

  draw_lines(points, xlim, ylim) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add('lines');
    group.setAttribute('transform', 'scale(1, -1)');

    var last = undefined;

    const range = (lim) => lim[1] == lim[0] ? 1 : lim[1] - lim[0];
    const t = (v, lim) => (v - lim[0]) / range(lim);

    points.forEach((point) => {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.classList.add('line');
      if (last) {
        line.setAttribute('x1', `${100 * t(last[0], xlim)}%`);
        line.setAttribute('y1', `${100 * t(last[1], ylim)}%`);
        line.setAttribute('x2', `${100 * t(point[0], xlim)}%`);
        line.setAttribute('y2', `${100 * t(point[1], ylim)}%`);
      }
      last = point;

      group.appendChild(line);
    });

    return group;
  }

  draw_points(points, tooltips, xlim, ylim) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add('points');
    group.setAttribute('transform', 'scale(1, -1)');

    const range = (lim) => lim[1] == lim[0] ? 1 : lim[1] - lim[0];
    const t = (v, lim) => (v - lim[0]) / range(lim);

    points.forEach((point, i) => {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.classList.add('point');
      circle.setAttribute('cx', `${100 * t(point[0], xlim)}%`);
      circle.setAttribute('cy', `${100 * t(point[1], ylim)}%`);
      circle.setAttribute('r', 5);

      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = tooltips[i];
      circle.appendChild(title);

      group.appendChild(circle);
    });

    return group;
  }

  draw_bars(bars, tooltips, width) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add('bars');
    group.setAttribute('transform', 'scale(1, -1)');

    const max_height = Math.max(...bars);
    const stride = (width / bars.length) + (1 - width) / (bars.length - 1);

    bars.forEach((height, i) => {
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.classList.add('bar');
      rect.setAttribute('x', `${100 * stride * i}%`);
      rect.setAttribute('y', 0);
      rect.setAttribute('width', `${100 * stride * width}%`);
      rect.setAttribute('height', `${100 * height / max_height}%`);

      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = tooltips[i];
      rect.appendChild(title);

      group.appendChild(rect);
    });

    return group;
  }
};

class LineChart extends Chart {
  constructor() {
    super(document.createElementNS("http://www.w3.org/2000/svg", "svg"));
    this.elem.classList.add('chart');
    this.elem.classList.add('line-chart');
  }

  plot({points, xlim, ylim, format, classes}) {
    const plot = this.create_plot();
    const tooltips = points.map(point => format(point));
    plot.appendChild(this.draw_axes(xlim, ylim));
    plot.appendChild(this.draw_lines(points, xlim, ylim));
    plot.appendChild(this.draw_points(points, tooltips, xlim, ylim));

    if (classes !== undefined) {
      for (const cls of classes) {
        plot.classList.add(cls);
      }
    }

    this.elem.appendChild(plot);

    return new Widget(plot);
  }
};

class Histogram extends Chart {
  constructor() {
    super(document.createElementNS("http://www.w3.org/2000/svg", "svg"));
    this.elem.classList.add('chart');
    this.elem.classList.add('histogram');
  }

  plot({values, n, format}) {
    const max = Math.max(...values);
    const min = Math.min(...values);
    const bins = new Array(n).fill(0);
    const bin_width = (max - min) / (n - 1);

    values.forEach((v) => {
      const idx = Math.floor((v - min) / bin_width);
      bins[idx] += 1;
    });

    const xlim = [ 0, n ];
    const ylim = [ 0, Math.max(...bins) ];
    const plot = this.create_plot();
    const tooltips = bins.map((bin,i) => `${format(min + i*bin_width)} to ${format(min + (i+1)*bin_width)}: ${bin}`);
    plot.appendChild(this.draw_axes(xlim, ylim));
    plot.appendChild(this.draw_bars(bins, tooltips, 0.8));

    this.elem.appendChild(plot);

    return new Widget(plot);
  }
}

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

const room_link = function(o) {
  if (o === undefined) {
    return undefined;
  } else if (!o.room_name || o.room_name == '') {
    return undefined;
  } else {
    return 'link';
  }
};

const seg_link = function(o) {
  if (o === undefined) {
    return undefined;
  } else if (!o.brief_name || o.brief_name == '') {
    return undefined;
  } else {
    return 'link';
  }
};

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
  if (o === undefined) {
    return undefined;
  } else if (!o.old) {
    return undefined;
  } else if (o.median_time < o.old.median_time) {
    return 'median-time-went-down';
  } else if (o.median_time > o.old.median_time) {
    return 'median-time-went-up';
  }
};

const ssb = function(o) {
  if (o === undefined) {
    return undefined;
  } else if (!o.old) {
    return undefined;
  } else if (o.best_time < o.old.best_time) {
    return 'best-time-went-down';
  }
};

const sssob = function(o) {
  if (o === undefined) {
    return undefined;
  } else if (!o.old) {
    return undefined;
  } else if (o.sum_of_best_times < o.old.sum_of_best_times) {
    return 'sum-of-best-times-went-down';
  }
};

const room_times_columns = [
  { label: "Room",   get: o => o.room_name,       cls: [ room_link  ],
                     onclick: o => show_room_history(o.room) },
  { label: "#",      get: o => o.attempts,        cls: [ 'numeric' ]   },
  { label: "Type",   get: o => o.type,            cls: [ 'time-type' ] },
  { label: "Time",   get: o => fc(o.time),        cls: [ 'time', tc ]  },
  { label: "Avg",    get: o => fc(o.avg_time),    cls: [ 'time' ]      },
  { label: "Median", get: o => fc(o.median_time), cls: [ 'time' ]      },
  { label: "Best",   get: o => fc(o.best_time),   cls: [ 'time' ]      },
  // TODO: P25, P75
];
const room_times_table = new Table(room_times_columns);
const room_times_div = new Widget(document.getElementById('room-times'));
room_times_div.elem.appendChild(room_times_table.elem);

const segment_times_columns = [
  { label: "Room",         get: o => o.room_name,                     cls: [ room_link ],
                           onclick: o => show_room_history(o.room)                       },
  { label: "#",            get: o => o.attempts,                      cls: [ 'numeric' ]  },
  { label: "Time",         get: o => fc(o.time),                      cls: [ 'time', tc ] },
  // { label: "Old Median",get: o => fc(o.median_time),               cls: [ 'time' ]     },
  { label: "\u00b1Median", get: o => fc_delta(o.time, o.median_time), cls: [ 'time' ]     },
  // { label: "Old Best",  get: o => fc(o.best_time),                 cls: [ 'time' ]     },
  { label: "\u00b1Best",   get: o => fc_delta(o.time, o.best_time),   cls: [ 'time' ]     },
];
const segment_times_table = new Table(segment_times_columns);
const segment_times_div = new Widget(document.getElementById('segment-times'));
segment_times_div.elem.appendChild(segment_times_table.elem);

const segment_stats_columns = [
  { label: "Segment",    get: o => o.brief_name,                         cls: [ seg_link ],
                         onclick: o => show_segment_history(o.id)                             },
  { label: "#",          get: o => o.success_count,                      cls: [ 'numeric' ]   },
  { label: "%",          get: o => pct(o.success_rate),                  cls: [ 'numeric' ]   },
  { label: "Median",     get: o => fc(o.median_time),                    cls: [ 'time', ssm ] },
  { label: "\u00b1Best", get: o => fc_delta(o.median_time, o.best_time), cls: [ 'time', ssb ] },
  { label: "\u00b1SOB",  get: o => fc_delta(o.median_time, o.sum_of_best_times), cls: [ 'time', sssob ] },
];
const segment_stats_table = new Table(segment_stats_columns);
const segment_stats_div = new Widget(document.getElementById('segment-stats'));
segment_stats_div.elem.appendChild(segment_stats_table.elem);

const segment_stats_footer_columns = [
  { label: "Segment",    get: o => o.brief_name,                             },
  { label: "#",          get: o => '',                                       },
  { label: "%",          get: o => '',                                       },
  { label: "Median",     get: o => fc(o.median_time),   cls: [ 'time', ssm ] },
  { label: "\u00b1Best", get: o => fc_delta(o.median_time, o.best_time) + '\n' + fc(o.best_time),         cls: [ 'time', ssb ]   },
  { label: "\u00b1SOB",  get: o => fc_delta(o.median_time, o.sum_of_best_times) + '\n' + fc(o.sum_of_best_times), cls: [ 'time', sssob ] },
];

const attempt_history_columns = [
  {                label: "Timestamp", get: o => ts(o.timestamp),                 },
  { group: "Room", label: "Game",      get: o => fc(o.room.game), cls: [ 'time' ] },
  { group: "Room", label: "Real",      get: o => fc(o.room.real), cls: [ 'time' ] },
  { group: "Room", label: "Lag",       get: o => fc(o.room.lag),  cls: [ 'time' ] },
  { group: "Door", label: "Game",      get: o => fc(o.door.game), cls: [ 'time' ] },
  { group: "Door", label: "Real",      get: o => fc(o.door.real), cls: [ 'time' ] },
  { group: "Door", label: "Lag",       get: o => fc(o.door.lag),  cls: [ 'time' ] },
];
const attempt_history_table = new Table(attempt_history_columns);
const attempt_history_div = new Widget(document.getElementById('attempt-history'));
document.getElementById('attempt-history-table').appendChild(attempt_history_table.elem);

const attempt_history_chart = new LineChart();
document.getElementById('attempt-history-chart').appendChild(attempt_history_chart.elem);

const attempt_histogram = new Histogram();
document.getElementById('attempt-histogram').appendChild(attempt_histogram.elem);

for (const elem of document.querySelectorAll('#attempt-history-chart-buttons input[type="radio"]')) {
  elem.addEventListener('change', function(event) {
    show_active_attempt_history_chart();
  });
}

for (const elem of document.querySelectorAll('#attempt-histogram-buttons input[type="radio"]')) {
  elem.addEventListener('change', function(event) {
    show_active_attempt_histogram();
  });
}

const attempt_history_close_button = new Widget(document.getElementById('attempt-history-close-button'));
attempt_history_close_button.elem.addEventListener('click', () => {
  attempt_history_div.hide();
});

const attempt_history_name = new Widget(document.getElementById('attempt-history-name'));

const gutter = new Widget(document.getElementById("gutter"));

const help_box = new Widget(document.getElementById("help"));

const scroll_changed = function(elem) {
  const scroll_top = bottom_panel.elem.scrollTop;
  const scroll_bot = bottom_panel.elem.scrollHeight - bottom_panel.elem.clientHeight - bottom_panel.elem.scrollTop;

  if (scroll_top > 50) {
    bottom_panel.elem.classList.add('top-shadow');
  } else {
    bottom_panel.elem.classList.remove('top-shadow');
  }

  if (scroll_bot > 50) {
    bottom_panel.elem.classList.add('bottom-shadow');
  } else {
    bottom_panel.elem.classList.remove('bottom-shadow');
  }
};

const bottom_panel = new Widget(document.getElementById('bottom-panel'));

bottom_panel.elem.addEventListener('scroll', (event) => {
  scroll_changed(event.target);
});

document.addEventListener('keydown', (event) => {
  if (event.key == 'r' || event.key == 'R') {
    console.log('- Switched to room timer -')
    room_times_div.show()
    segment_times_div.hide()
  } else if (event.key == 's' || event.key == 'S') {
    console.log('- Switched to segment timer -')
    segment_times_div.show()
    room_times_div.hide()
  } else if (event.key == '?') {
    help_box.show();
  } else if (event.key == ' ') {
    help_box.hide();
  }
});

// Used for segment timer panel
var num_segments = 0;
var current_segment_time_node = undefined;

// Used for segment stats panel
const segment_stats_by_id = { };
const segment_stats_rows_by_id = { };
var last_updated_segment = undefined;
var last_updated_segment_row = undefined;

const handle_new_room_time = function(data) {
  help_box.hide();

  room_times_table.append_row({
    room: data.room,
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
  room_times_table.append_row({
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
  room_times_table.append_row({
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
  room_times_table.append_row({
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
  room_times_table.append_row({
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
  segment_times_table.append_row({
    room: data.room,
    room_name: data.room.room_name,
    attempts: data.room_in_segment.attempts,
    time: data.room_in_segment.time,
    median_time: data.room_in_segment.prev_median_time,
    best_time: data.room_in_segment.prev_best_time,
    p25_time: data.room_in_segment.prev_p25_time,
    p75_time: data.room_in_segment.prev_p75_time,
  });
  current_segment_time_node = segment_times_table.append_row({
    room_name: 'Segment',
    attempts: data.segment.attempts,
    time: data.segment.time,
    median_time: data.segment.prev_median_time,
    best_time: data.segment.prev_best_time,
    p25_time: data.segment.prev_p25_time,
    p75_time: data.segment.prev_p75_time,
  });
};

const handle_new_segment = function(data) {
  if (num_segments > 0) {
    segment_times_table.append_blank_line();
  }
  num_segments += 1;
  current_segment_time_node = undefined;
};

var old_segment_totals = { };

const handle_segment_stats = function(data) {
  data.segments.forEach((segment) => {
    const row = segment_stats_rows_by_id[segment.id];
    if (row) {
      // Clear out any colors from the last updated row
      if (last_updated_segment_row) {
        last_updated_segment_row.elem.classList.remove('most-recent-segment');
        last_updated_segment_row.update({
          old: undefined,
          ...last_updated_segment,
        });
      }

      // Update the row for this segment, with colors indicating any
      // improvement
      const old_segment = segment_stats_by_id[segment.id];
      row.update({
        old: old_segment,
        ...segment
      });
      row.elem.classList.add('most-recent-segment');
      row.elem.scrollIntoView({ behavior: 'smooth', block: 'center' })

      // Save segment stats for next time this row is updated
      segment_stats_by_id[segment.id] = segment;

      // Save last updated segment/row so we can clear colors when the
      // next segment is updated
      last_updated_segment = segment;
      last_updated_segment_row = row;
    } else {
      segment_stats_rows_by_id[segment.id] = segment_stats_table.append_row(segment)
      segment_stats_by_id[segment.id] = segment;
    }
  });

  var segment_totals = {
    median_time: 0,
    best_time: 0,
    sum_of_best_times: 0,
  }

  for (const [ id, stats ] of Object.entries(segment_stats_by_id)) {
    segment_totals.median_time += stats.median_time;
    segment_totals.best_time += stats.best_time;
    segment_totals.sum_of_best_times += stats.sum_of_best_times;
  }

  segment_stats_table.clear_footer();

  // TODO: Update totals row instead of re-creating it to avoid reflow
  const row = segment_stats_table.append_footer_row({
      brief_name: 'Total',
      success_count: undefined,
      success_rate: undefined,
      old: old_segment_totals,
      ...segment_totals,
  }, segment_stats_footer_columns);

  old_segment_totals = segment_totals;

  segment_stats_div.show();
  scroll_changed(bottom_panel.elem);
  gutter.show();
};

const attempt_history_plots = { };
const attempt_histogram_plots = { };

const show_active_attempt_history_chart = function() {
  const active_what_elems = document.querySelectorAll('#attempt-history-charts input[name="attempt-history-chart-what"]:checked');
  const active_time_type_elems = document.querySelectorAll('#attempt-history-charts input[name="attempt-history-chart-time-type"]:checked');

  for (const chart of Object.values(attempt_history_plots)) {
    chart.hide();
  }

  for (const active_what_elem of active_what_elems) {
    for (const active_time_type_elem of active_time_type_elems) {
      const active_what = active_what_elem.value;
      const active_time_type = active_time_type_elem.value;
      const active_plot = attempt_history_plots[`${active_what}-${active_time_type}`];
      active_plot.show();
    }
  }
};

const show_active_attempt_histogram = function() {
  const active_what_elems = document.querySelectorAll('#attempt-history-charts input[name="attempt-histogram-what"]:checked');
  const active_time_type_elems = document.querySelectorAll('#attempt-history-charts input[name="attempt-histogram-time-type"]:checked');

  for (const chart of Object.values(attempt_histogram_plots)) {
    chart.hide();
  }

  for (const active_what_elem of active_what_elems) {
    for (const active_time_type_elem of active_time_type_elems) {
      const active_what = active_what_elem.value;
      const active_time_type = active_time_type_elem.value;
      const active_plot = attempt_histogram_plots[`${active_what}-${active_time_type}`];
      active_plot.show();
    }
  }
};

const show_attempt_history = function(name, data) {
  // {"room": {"game": 463.0, "real": 463.0, "lag": 0.0}, "door": {"game": 120.0, "real": 162.0, "lag": 42.0}}

  attempt_history_name.clear();
  attempt_history_name.elem.appendChild(document.createTextNode(name));

  if (attempt_history_table.body) {
    attempt_history_table.body.clear();
  }

  attempt_history_chart.clear();
  attempt_histogram.clear();

  for (const what of [ 'room', 'door' ]) {
    for (const time_type of [ 'real', 'game', 'lag' ]) {
      const times = data.times.map(t => t[what][time_type]);
      const points = times.map((t,i) => [ i, t ]);
      const xlim = [ 0, points.length ];
      const ylim = [ Math.min(...times), Math.max(...times) ];
      const name = `${what}-${time_type}`;

      const history_plot = attempt_history_chart.plot({
        points: points,
        xlim: xlim,
        ylim: ylim,
        format: p => fc(p[1]),
        classes: [ 'hidden' ],
      });

      const histogram_plot = attempt_histogram.plot({
        values: times,
        n: 27,
        format: v => fc(v),
        classes: [ 'hidden' ],
      });

      attempt_history_plots[name] = history_plot;
      attempt_histogram_plots[name] = histogram_plot;
    }
  }

  show_active_attempt_history_chart();
  show_active_attempt_histogram();

  data.times.forEach((times) => {
    attempt_history_table.append_row(times);
  });

  attempt_history_div.show();
};

const handle_room_history = function(data) {
  show_attempt_history(data.room.room_name, data);
}

const handle_segment_history = function(data) {
  show_attempt_history(data.segment.name, data);
};

class TimerClient {
  constructor(url, reconnect_interval, on_new_room_time, on_new_segment, on_segment_stats, on_room_history, on_segment_history) {
    this.url = url;
    this.reconnect_interval = reconnect_interval;
    this.handle_new_room_time = on_new_room_time;
    this.handle_new_segment = on_new_segment;
    this.handle_segment_stats = on_segment_stats;
    this.handle_room_history = on_room_history;
    this.handle_segment_history = on_segment_history;

    this.open_handler = (e) => this.handle_open(e);
    this.close_handler = (e) => this.handle_close(e);
    this.message_handler = (e) => this.handle_message(e);

    this.socket = undefined;
    this.connect();
  }

  connect() {
    this.finish();

    this.socket = new WebSocket(url);

    this.socket.addEventListener('open', this.open_handler);
    this.socket.addEventListener('close', this.close_handler);
    this.socket.addEventListener('message', this.message_handler);
  }

  finish() {
    if (this.socket) {
      this.socket.removeEventListener('open', this.open_handler);
      this.socket.removeEventListener('close', this.close_handler);
      this.socket.removeEventListener('message', this.message_handler);
    }
  }

  handle_open(event) {
  }

  handle_close(event) {
    setTimeout(() => this.connect(), this.reconnect_interval);
  }

  handle_message(event) {
    console.log(event.data);
    const msg = JSON.parse(event.data);
    const type = msg[0];
    const data = msg[1];
    if (type == 'new_room_time') {
      this.handle_new_room_time(data);
    } else if (type == 'new_segment') {
      this.handle_new_segment(data);
    } else if (type == 'segment_stats') {
      this.handle_segment_stats(data);
    } else if (type == 'room_history') {
      this.handle_room_history(data);
    } else if (type == 'segment_history') {
      this.handle_segment_history(data);
    }
  }

  fetch_room_history(tid) {
    // TODO: show spinner to indicate data is loading?
    const msg = JSON.stringify([ 'room_history', { room: tid } ]);
    this.socket.send(msg);
  }

  fetch_segment_history(segment_id) {
    // TODO: show spinner to indicate data is loading?
    const msg = JSON.stringify([ 'segment_history', { segment: segment_id } ]);
    this.socket.send(msg);
  }
}

const params = new URLSearchParams(location.search);
const port = params.get('port');
const url = `ws://localhost:${port}`;
const timer_client = new TimerClient(url, 10000, handle_new_room_time, handle_new_segment, handle_segment_stats, handle_room_history, handle_segment_history);

const show_room_history = function(room) {
  // TODO: no room history for segment row
  if (room) {
    timer_client.fetch_room_history(room);
  }
}

const show_segment_history = function(segment_id) {
  if (segment_id) {
    timer_client.fetch_segment_history(segment_id);
  }
}
