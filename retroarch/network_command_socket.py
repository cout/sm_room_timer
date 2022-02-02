import socket
import select

class NetworkCommandSocket(object):
  def __init__(self, port=55355, addr='127.0.0.1'):
    try:
      self.connect(addr, port)
      print("Connected on %s" % port)
      self.read_core_ram(0, 0)
      print("OK")
    except:
      port = 55354
      self.connect(addr, port)
      print("Connected on %s" % port)
      self.read_core_ram(0, 0)
      print("OK")

  def connect(self, addr, port):
    self.port = port
    self.addr = addr

    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket.connect((addr, port))

  def send_command(self, msg):
    self.socket.sendmsg([msg.encode()])
    r, w, e = select.select([self.socket], [], [], 1)
    if len(r) > 0:
      try:
        msg, ancdata, flags, addr = self.socket.recvmsg(1024)
      except ConnectionRefusedError:
        return None
      response = msg.split()[2:]
      return response
    else:
      return None

  def read_core_ram(self, addr, size):
    msg = "READ_CORE_RAM %x %d\n" % (addr, size)
    response = self.send_command(msg)
    if response is not None:
      vals = [ int(field, 16) for field in response ]
      return vals
    else:
      return None
