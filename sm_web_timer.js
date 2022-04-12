const params = new URLSearchParams(location.search);
const port = params.get('port');
const socket = new WebSocket(`ws://localhost:${port}`)

socket.addEventListener('open', function (event) {
  console.error('open');
});

socket.addEventListener('close', function (event) {
  console.error('close');
});

socket.addEventListener('message', function (event) {
  console.error('message', event);
});
