const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 5000;

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

const server = http.createServer((req, res) => {
  let filePath;

  if (req.url === "/" || req.url === "/index.html") {
    filePath = path.join(__dirname, "preview", "index.html");
  } else if (req.url === "/audac-mtx-card.js") {
    filePath = path.join(__dirname, "dist", "audac-mtx-card.js");
  } else {
    filePath = path.join(__dirname, "preview", req.url);
  }

  const ext = path.extname(filePath);
  const contentType = MIME[ext] || "application/octet-stream";

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": contentType,
      "Cache-Control": "no-cache",
    });
    res.end(content);
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Audac MTX Card Preview running at http://0.0.0.0:${PORT}`);
});
