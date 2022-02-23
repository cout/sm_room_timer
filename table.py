class Cell(object):
  def __init__(self, text, color=None, justify='left'):
    self.text = text
    self.color = color
    self.justify = justify

  def __len__(self):
    return len(self.text)

  def __repr__(self):
    return repr(self.text)

  def __str__(self):
    return str(self.text)

  def __iter__(self):
    return iter(self.text)

  def width(self):
    return len(str(self.text))

  def render(self, width):
    text = "\033[%sm%s\033[m" % ('' if self.color is None else self.color, self.text)
    spacing = ' ' * (width - self.width())
    if self.justify == 'left':
      return text + spacing
    elif self.justify == 'right':
      return spacing + text
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

  def render(self):
    width = { }
    for row in self.rows:
      for idx, cell in enumerate(row):
        width[idx] = max(cell.width(), width.get(idx, 0))

    lines = [ ]
    for row in self.rows:
      lines.append('  '.join([ cell.render(width=width[idx]) for idx, cell in enumerate(row) ]))

    return "\n".join(lines)
