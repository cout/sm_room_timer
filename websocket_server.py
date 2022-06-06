import asyncio
import websockets
import queue
from threading import Thread

class WebsocketServerSession(object):
  def __init__(self, sock, server):
    self.sock = sock
    self.server = server

  def send(self, msg):
    self.server.put_command(WebsocketServer.SEND, (self, msg))

class WebsocketServer(object):
  # Commands
  class SHUTDOWN: pass
  class BROADCAST: pass
  class SEND: pass

  # Events
  class CONNECTED: pass
  class DISCONNECTED: pass

  def __init__(self, port):
    self.port = port
    self.sessions = set()
    self.loop = None
    self.command_queue = None
    self.event_queue = queue.Queue()
    self.thread = Thread(target=self.run)

  def start(self):
    self.loop = None
    self.thread.start()
    while self.loop is None:
      pass

  def stop(self):
    self.put_command(WebsocketServer.SHUTDOWN, None)
    self.thread.join()

  def broadcast(self, event):
    self.put_command(WebsocketServer.BROADCAST, event)

  def put_command(self, cmd, msg):
    def put_command():
      self.command_queue.put_nowait((cmd, msg))
    self.loop.call_soon_threadsafe(put_command)

  def get_event_nowait(self):
    try:
      if self.event_queue.empty():
        return None
      return self.event_queue.get_nowait()
    except queue.Empty:
      return None

  def is_alive(self):
    return self.thread.is_alive()

  def run(self):
    self.loop = asyncio.new_event_loop()
    try:
      self.loop.run_until_complete(self._run())
    finally:
      self.loop.stop()

  async def _run(self):
    self.command_queue = asyncio.Queue()
    async with websockets.serve(self.serve, 'localhost', self.port):
      while True:
        cmd, msg = await self.command_queue.get()
        if cmd is WebsocketServer.SHUTDOWN:
          break
        elif cmd is WebsocketServer.BROADCAST:
          # TODO: a slow socket can slow everyone down
          for session in self.sessions:
            await session.sock.send(msg)
        elif cmd is WebsocketServer.SEND:
          session, msg = msg
          if session in self.sessions:
            await session.sock.send(msg)
        else:
          raise RuntimeError("Unknown command %s" % cmd)

  async def serve(self, sock, uri=None):
    session = WebsocketServerSession(sock, self)
    self.sessions.add(session)
    self.event_queue.put_nowait((WebsocketServer.CONNECTED, session))
    try:
      # async for message in session.sock:
        # pass
      await session.sock.wait_closed()
    finally:
      self.event_queue.put_nowait((WebsocketServer.DISCONNECTED, session))
      self.sessions.remove(session)
