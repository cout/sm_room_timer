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

  def render(self, width, margin_width):
    color_on = "\033[%sm" % ('' if self.color is None else self.color)
    text = "%s" % self.text
    if self.max_width: text = text[0:self.max_width]
    color_off = "\033[m"
    spacing = ' ' * (width - self.width())
    margin = ' ' * margin_width
    if self.justify == 'left':
      return margin + color_on + text + spacing + color_off
    elif self.justify == 'right':
      return margin + color_on + spacing + text + color_off
    else:
      raise ValueError("Invalid value for justify: %s" % self.justify)

class Table(object):
  def __init__(self):
    self.rows = [ ]

  def append(self, row):
    self.rows.append(row)

  def __len__(self):
    return len(self.rows)

  def __iter__(self):
    return iter(self.rows)

  def render_cell(self, cell, width, idx):
    margin_width = 0 if idx == 0 else 2
    return cell.render(width=width, margin_width=margin_width)

  def render(self):
    width = { }
    for row in self.rows:
      for idx, cell in enumerate(row):
        width[idx] = max(cell.width(), width.get(idx, 0))

    lines = [ ]
    for row in self.rows:
      rendered_cells = [ self.render_cell(cell, width[idx], idx) for idx, cell in enumerate(row) ]
      lines.append(''.join(rendered_cells))

    return "\n".join(lines)
