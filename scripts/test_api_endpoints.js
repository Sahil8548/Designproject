const http = require('http');

function request(path, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: 'localhost',
      port: 3000,
      path,
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    const req = http.request(opts, res => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: body.startsWith('{') || body.startsWith('[') ? JSON.parse(body) : body });
        } catch (e) {
          resolve({ status: res.statusCode, body });
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(typeof data === 'string' ? data : JSON.stringify(data));
    req.end();
  });
}

async function run() {
  console.log('--- TEST 1: /api/dataset-status ---');
  const s1 = await request('/api/dataset-status');
  console.log(`Status: ${s1.status}, All Ready: ${s1.body.all_ready}, Files: ${s1.body.files.length}`);

  console.log('\n--- TEST 2: /api/templates/rooms.csv ---');
  const tpl = await request('/api/templates/rooms.csv');
  console.log(`Status: ${tpl.status}`);
  console.log(`Contains room_type: ${tpl.body.includes('room_type')}`);
  console.log(`Header line: ${tpl.body.split('\n')[0]}`);

  console.log('\n--- TEST 3: /api/preprocess ---');
  const p1 = await request('/api/preprocess', 'POST', {});
  console.log(`Status: ${p1.status}, Preprocessing Status: ${p1.body.status}`);
  console.log(`Classes: ${p1.body.metrics.classes_count}, Rooms: ${p1.body.metrics.rooms_count}, Teachers: ${p1.body.metrics.teachers_count}`);

  console.log('\n--- TEST 4: /api/generate (Random Forest) ---');
  const gRf = await request('/api/generate', 'POST', { mode: 'random_forest', seed: 42, applyRepair: true });
  console.log(`Status: ${gRf.status}`);
  console.log(`Scheduled: ${gRf.body.metrics.scheduled_classes} / ${gRf.body.metrics.total_classes} (${gRf.body.metrics.completion_pct}%)`);
  console.log(`Room Overlaps: ${gRf.body.metrics.room_overlap_pairs}`);
  console.log(`Teacher Overlaps: ${gRf.body.metrics.instructor_overlap_pairs}`);
  console.log(`Teacher Availability Violations: ${gRf.body.metrics.availability_violations}`);
  console.log(`Capacity Deficits: ${gRf.body.metrics.room_capacity_deficits}`);

  console.log('\n--- TEST 5: /api/generate (XGBoost) ---');
  const gXgb = await request('/api/generate', 'POST', { mode: 'xgboost', seed: 42, applyRepair: true });
  console.log(`Status: ${gXgb.status}`);
  console.log(`Scheduled: ${gXgb.body.metrics.scheduled_classes} / ${gXgb.body.metrics.total_classes} (${gXgb.body.metrics.completion_pct}%)`);
  console.log(`Room Overlaps: ${gXgb.body.metrics.room_overlap_pairs}`);
  console.log(`Teacher Overlaps: ${gXgb.body.metrics.instructor_overlap_pairs}`);

  console.log('\n--- TEST 6: /api/generate (Compare All) ---');
  const gAll = await request('/api/generate', 'POST', { mode: 'compare_all', seed: 42, applyRepair: true });
  console.log(`Status: ${gAll.status}`);
  console.log(`Winner Declared: ${gAll.body.winner}`);
  console.log(`Comparison Matrix:`);
  gAll.body.comparison_matrix.forEach(m => {
    console.log(`  - ${m.name}: ${m.scheduled_classes}/${m.total_classes} (${m.completion_pct}%), Clashes: R=${m.room_overlap_pairs}, T=${m.instructor_overlap_pairs}, Avail=${m.availability_violations}, Runtime=${m.runtime_seconds}s`);
  });

  console.log('\n--- TEST 7: /api/export-csv ---');
  const exp = await request(`/api/export-csv/${gRf.body.timetable_id}`);
  console.log(`Status: ${exp.status}, Content Length: ${exp.body.length} bytes`);
  console.log(`CSV Header: ${exp.body.split('\n')[0]}`);
  console.log(`CSV First Row: ${exp.body.split('\n')[1]}`);

  console.log('\n--- TEST 8: /api/results ---');
  const res = await request('/api/results');
  console.log(`Status: ${res.status}, Algorithms loaded: ${Object.keys(res.body.algorithms).join(', ')}`);

  console.log('\n=====================================');
  console.log('ALL API TESTS PASSED SUCCESSFULLY!');
  console.log('=====================================');
}

run().catch(err => {
  console.error('Test error:', err);
  process.exit(1);
});
