const http = require('http');

const hostname = '0.0.0.0'; // Listen on all network interfaces
const port = 3000;

const fake_db = " database connection string";

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello from Dockerized Node.js!\n');
});

server.listen(port, hostname, () => {
  console.log(`Server running internally on port ${port}`);
});