import socket
import select

class DefaultLogger(object):
  def log(self, x):
    pass

  def log_debug(self, x):
    pass

  def log_verbose(self, x):
    pass

class NetworkCommandSocket(object):
  def __init__(self, port=55355, addr='127.0.0.1', logger=None):
    self.logger = logger or DefaultLogger()

    try:
      self.connect(addr, port)
      self.logger.log("Connected on %s" % port)
      self.read_core_ram(0, 0)
      self.logger.log("OK")
    except:
      port = 55354
      self.connect(addr, port)
      self.logger.log("Connected on %s" % port)
      self.read_core_ram(0, 0)
      self.logger.log("OK")

  def connect(self, addr, port):
    self.port = port
    self.addr = addr

    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.socket.connect((addr, port))

  def close(self):
    self.socket.close()

  def send_command(self, msg):
    self.socket.sendmsg([msg.encode()])

  def read_response(self):
    r, w, e = select.select([self.socket], [], [], 1)
    if len(r) > 0:
      try:
        msg, ancdata, flags, addr = self.socket.recvmsg(1024)
      except ConnectionRefusedError:
        self.logger.log("connection refused")
        return None
      return msg
    else:
      self.logger.log("connection timed out")
      return None

  def read_core_ram(self, addr, size):
    self.send_read_core_ram_command(addr, size)
    return self.read_read_core_ram_response(addr, size)

  def send_read_core_ram_command(self, addr, size):
    msg = "READ_CORE_RAM %x %d\n" % (addr, size)
    self.send_command(msg)

  def send_read_core_ram_multi_command(self, addrs):
    for (addr, size) in addrs:
      self.send_read_core_ram_command(addr, size)

  def read_read_core_ram_response(self, addr, size):
    while True:
      response = self.read_response()
      if response is None:
        return None
      words = response.split()
      if words[0] != b'READ_CORE_RAM':
        self.logger.log(
            "Expected response for %s but got response for %s: %s" % (
              'READ_CORE_RAM', words[0], response))
        continue
      if words[1] != b'%x' % addr:
        self.logger.log(
            "Expected response for address %s but got response for address %s: %s" % (
              b'%x' % addr, words[1], response))
        continue
      vals = [ int(field, 16) for field in words[2:] ]
      return vals

  def read_core_ram_multi(self, addrs):
    self.send_read_core_ram_multi_command(addrs)
    return [ self.read_read_core_ram_response(addr, size) for (addr, size) in addrs ]
