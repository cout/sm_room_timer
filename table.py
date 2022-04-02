class DefaultRenderer(object):
  def render_cell_contents(self, cell, width):
    color_on = "\033[%sm" % ('' if cell.color is None else cell.color)
    color_off = "\033[m"

    spacing = ' ' * (width - cell.width())
    text = "%s" % cell.text
    if cell.max_width: text = text[0:cell.max_width]

    if cell.justify == 'left':
      return color_on + text + spacing + color_off
    elif cell.justify == 'right':
      return color_on + spacing + text + color_off
    else:
      raise ValueError("Invalid value for justify: %s" % cell.justify)

  def render_cell_margin(self, margin_width):
    return ' ' * margin_width

  def render_cell(self, cell, width, idx, cell_margin_width=2):
    margin = self.render_cell_margin(cell_margin_width) if idx > 0 else ''
    contents = self.render_cell_contents(cell, width)
    return margin + contents

  def compute_widths(self, table):
    width = { }

    for row in table.rows:
      for idx, cell in enumerate(row):
        width[idx] = max(cell.width(), width.get(idx, 0))

    return width

  def render_row(self, row, widths, **kwargs):
      cells = [ self.render_cell(cell, widths[idx], idx, **kwargs)
          for idx, cell in enumerate(row) ]
      return ''.join(cells)

  def render_rows(self, table, widths, **kwargs):
    rows = [ self.render_row(row, widths, **kwargs) for row in table.rows ]
    return "\n".join(rows)

  def render(self, table, **kwargs):
    widths = self.compute_widths(table)
    return self.render_rows(table, widths, **kwargs)

class CompactRenderer(DefaultRenderer):
  def render_cell_margin(self, margin_width, divider='│', divider_brightness=3):
    left = ' ' * (margin_width // 2)
    right = ' ' * ((margin_width - 1) // 2)
    color = '38;5;%s' % (232 + divider_brightness)
    color_on = "\033[%sm" % color
    color_off = "\033[m"
    return ''.join((left, color_on, divider, color_off, right))

  def render_cell(self, cell, width, idx, cell_margin_width=1):
    margin = self.render_cell_margin(cell_margin_width) if idx > 0 else ''
    contents = self.render_cell_contents(cell, width)
    return margin + contents

class Cell(object):
  def __init__(self, text, color=None, justify='left', max_width=None):
    self.text = text
    self.color = color
    self.justify = justify
    self.max_width = max_width

  def __len__(self):
    return len(self.text)

  def __repr__(self):
    return repr(self.text)

  def __str__(self):
    return str(self.text)

  def __iter__(self):
    return iter(self.text)

  def width(self):
    if self.max_width is None:
      return len(str(self.text))
    else:
      return min(len(str(self.text)), self.max_width)

class Table(object):
  def __init__(self, renderer=None):
    self.rows = [ ]
    self.renderer = renderer or DefaultRenderer()

  def append(self, row):
    self.rows.append(row)

  def __len__(self):
    return len(self.rows)

  def __iter__(self):
    return iter(self.rows)

  def render(self, *args, **kwargs):
    return self.renderer.render(self, *args, **kwargs)
