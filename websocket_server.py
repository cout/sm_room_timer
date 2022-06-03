import asyncio
import websockets
from queue import Queue
from threading import Thread

class WebsocketServerSession(object):
  def __init__(self, sock, server):
    self.sock = sock
    self.server = server

class WebsocketServer(object):
  class SHUTDOWN: pass

  def __init__(self, port):
    self.port = port
    self.sessions = set()
    self.loop = None
    self.broadcast_queue = None
    self.thread = Thread(target=self.run)

  def start(self):
    self.loop = None
    self.thread.start()
    while self.loop is None:
      pass

  def stop(self):
    self.broadcast(WebsocketServer.SHUTDOWN)
    self.thread.join()

  def broadcast(self, event):
    def broadcast():
      self.broadcast_queue.put_nowait(event)
    self.loop.call_soon_threadsafe(broadcast)

  def is_alive(self):
    return self.thread.is_alive()

  def run(self):
    self.loop = asyncio.new_event_loop()
    try:
      self.loop.run_until_complete(self._run())
    finally:
      self.loop.stop()

  async def _run(self):
    self.broadcast_queue = asyncio.Queue()
    async with websockets.serve(self.serve, 'localhost', self.port):
      while True:
        msg = await self.broadcast_queue.get()
        if msg is WebsocketServer.SHUTDOWN: break
        # TODO: a slow socket can slow everyone down
        for session in self.sessions:
          await session.sock.send(msg)

  async def serve(self, sock, uri=None):
    session = WebsocketServerSession(sock, self)
    self.sessions.add(session)
    try:
      # async for message in session.sock:
        # pass
      await session.sock.wait_closed()
    finally:
      self.sessions.remove(session)

