const socket = new WebSocket('ws://localhost:15000')

socket.addEventListener('open', function (event) {
  console.error('open');
});

socket.addEventListener('close', function (event) {
  console.error('close');
});

socket.addEventListener('message', function (event) {
  console.error('message', event);
});
