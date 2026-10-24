/**
 * Simulates Vercel Serverless Invocation of api/index.js and api/[...path].js
 */
const http = require('http');
const serverlessHandler = require('../api/index');
const catchallHandler = require('../api/[...path]');

function mockServerlessCall(handler, url, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    // Create a local transient http server wrapping the serverless handler
    const server = http.createServer((req, res) => {
      handler(req, res);
    });

    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      const opts = {
        hostname: '127.0.0.1',
        port: port,
        path: url,
        method: method,
        headers: body ? { 'Content-Type': 'application/json' } : {}
      };

      const req = http.request(opts, (res) => {
        let raw = '';
        res.on('data', chunk => raw += chunk);
        res.on('end', () => {
          server.close();
          try {
            const parsed = JSON.parse(raw);
            resolve({ status: res.statusCode, headers: res.headers, body: parsed });
          } catch (e) {
            resolve({ status: res.statusCode, headers: res.headers, body: raw });
          }
        });
      });

      req.on('error', (err) => {
        server.close();
        reject(err);
      });

      if (body) {
        req.write(typeof body === 'string' ? body : JSON.stringify(body));
      }
      req.end();
    });
  });
}

async function testServerless() {
  console.log('Testing api/index.js handler...');
  const res1 = await mockServerlessCall(serverlessHandler, '/api/dataset-status');
  console.log(`api/index -> /api/dataset-status: status ${res1.status}, all_ready: ${res1.body.all_ready}, files: ${res1.body.files ? res1.body.files.length : 0}`);
  if (res1.status !== 200 || !res1.body.all_ready) {
    throw new Error('api/index.js failed dataset-status check');
  }

  console.log('\nTesting api/[...path].js catch-all handler...');
  const res2 = await mockServerlessCall(catchallHandler, '/api/workflow/state');
  console.log(`api/[...path] -> /api/workflow/state: status ${res2.status}, current_stage: ${res2.body.current_stage}`);
  if (res2.status !== 200 || !res2.body.current_stage) {
    throw new Error('api/[...path].js failed workflow/state check');
  }

  console.log('\nTesting CORS Preflight in serverless handler...');
  const res3 = await mockServerlessCall(serverlessHandler, '/api/preprocess', 'OPTIONS');
  console.log(`api/index OPTIONS preflight: status ${res3.status}, allow-origin: ${res3.headers['access-control-allow-origin']}`);
  if (res3.status !== 204 || res3.headers['access-control-allow-origin'] !== '*') {
    throw new Error('CORS preflight failed');
  }

  console.log('\n=============================================');
  console.log('SERVERLESS HANDLER INVOCATION VERIFIED 100%!');
  console.log('=============================================');
}

testServerless().catch(err => {
  console.error('Serverless test failed:', err);
  process.exit(1);
});
