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

  def render_cell_margin(self, idx, margin_width):
    return ' ' * (margin_width if idx != 0 else 0)

  def render_cell(self, cell, width, idx, margin_width):
    return self.render_cell_margin(idx, margin_width) + self.render_cell_contents(cell, width)

  def compute_widths(self, table):
    width = { }

    for row in table.rows:
      for idx, cell in enumerate(row):
        width[idx] = max(cell.width(), width.get(idx, 0))

    return width

  def render(self, table, cell_margin_width=2):
    width = self.compute_widths(table)

    lines = [ ]
    for row in table.rows:
      rendered_cells = [ self.render_cell(cell, width[idx], idx, margin_width=cell_margin_width)
          for idx, cell in enumerate(row) ]
      lines.append(''.join(rendered_cells))

    return "\n".join(lines)

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
