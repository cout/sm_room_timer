import socket

class NetworkCommandSocket(object):
  def __init__(self, port=55355, addr='127.0.0.1'):
    try:
      self.connect(addr, port)
      self.read_core_ram(0, 0)
    except:
      port = 55354
      self.connect(addr, port)
      self.read_core_ram(0, 0)

  def connect(self, addr, port):
    self.port = port
    self.addr = addr

    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket.connect((addr, port))

  def read_core_ram(self, addr, size):
    msg = "READ_CORE_RAM %x %d\n" % (addr, size)
    self.socket.sendmsg([msg.encode()])
    msg, ancdata, flags, addr = self.socket.recvmsg(1024)
    vals = [ int(field, 16) for field in msg.split()[2:] ]
    return vals
