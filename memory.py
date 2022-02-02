class MemoryMixin(object):
  def short(self, addr):
    lo = self[addr] or 0
    hi = self[addr + 1] or 0
    return lo | hi << 8

  def bignum(self, addr, size):
    result = 0
    for i in range(0, size):
      octet = self[addr + i] or 0
      result |= octet << (8 * i)
    return result

class MemoryRegion(MemoryMixin):
  def __init__(self, addr, s):
    self.start = addr
    self.s = s

  @staticmethod
  def read_from(sock, addr, size):
    s = sock.read_core_ram(addr, size)
    if s is not None:
      return MemoryRegion(addr, s)
    else:
      return None

  def __getitem__(self, addr):
    return self.s[addr - self.start]

  def __len__(self):
    return len(self.s)

class SparseMemory(MemoryMixin):
  def __init__(self, *regions):
    self.regions = regions

  @staticmethod
  def read_from(sock, *addresses):
    regions = [ ]

    for start, length in addresses:
      region = MemoryRegion.read_from(sock, start, length)
      if region is None:
        return None
      regions.append(region)

    return SparseMemory(*regions)

  def __getitem__(self, addr):
    for region in self.regions:
      if addr >= region.start and addr < region.start + len(region):
        return region[addr]

    raise IndexError("address out of range")
