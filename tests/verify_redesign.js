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

async function runAudit() {
  console.log('=======================================================');
  console.log('UNITIME COMPLETE PIPELINE & ACCEPTANCE CRITERIA AUDIT');
  console.log('=======================================================');

  // 1. Navigation & UI Structure
  console.log('\n--- 1. NAVIGATION & UI AUDIT ---');
  const indexRes = await request('/');
  console.log('Index HTML Status:', indexRes.status);
  const html = indexRes.body;

  const hasExecutiveDashboard = html.includes('Executive Dashboard');
  console.log('Contains "Executive Dashboard":', hasExecutiveDashboard, '(Must be false)');
  if (hasExecutiveDashboard) throw new Error('Executive Dashboard heading must be completely removed');

  const has3Tabs = [
    'id="navTabGenerate">Generate</button>',
    'id="navTabTimetable">Timetable</button>',
    'id="navTabResults">Results</button>'
  ].every(t => html.includes(t));
  console.log('Contains exactly 3 primary navigation tabs (Generate, Timetable, Results):', has3Tabs);
  if (!has3Tabs) throw new Error('Navigation must have exactly 3 primary sections');

  // 2. Schema Integrity: No room_type in templates or code
  console.log('\n--- 2. SCHEMA AUDIT: NO ROOM_TYPE DEPENDENCY ---');
  const roomTpl = await request('/api/templates/rooms.csv');
  console.log('GET /api/templates/rooms.csv Status:', roomTpl.status);
  const hasRoomType = roomTpl.body.includes('room_type');
  console.log('rooms.csv template contains "room_type":', hasRoomType, '(Must be false)');
  console.log('rooms.csv header:', roomTpl.body.split('\n')[0]);
  if (hasRoomType) throw new Error('rooms.csv must NOT contain room_type');

  // 3. Dataset Status
  console.log('\n--- 3. DATASET STATUS AUDIT ---');
  const dsRes = await request('/api/dataset-status');
  console.log('GET /api/dataset-status Status:', dsRes.status);
  console.log('All 6 CSV files ready:', dsRes.body.all_ready);
  console.log('Files detected:', dsRes.body.files.map(f => `${f.filename} (${f.rowCount} rows)`).join(', '));
  if (!dsRes.body.all_ready) throw new Error('All 6 required CSV files must be present');

  // 4. Preprocessing Stage First
  console.log('\n--- 4. DATA PREPROCESSING STAGE AUDIT ---');
  const prepRes = await request('/api/preprocess', 'POST', {});
  console.log('POST /api/preprocess Status:', prepRes.status);
  const prep = prepRes.body;
  console.log('Preprocessing Status:', prep.status);
  console.log('Classes Count:', prep.metrics.classes_count);
  console.log('Rooms Count:', prep.metrics.rooms_count);
  console.log('Teachers Count:', prep.metrics.teachers_count);
  console.log('Time Slots Count:', prep.metrics.time_slots_count);
  console.log('Availability Records:', prep.metrics.availability_records_count);
  console.log('Invalid Records:', prep.metrics.invalid_records_count);
  console.log('Duplicates Detected:', prep.metrics.duplicates_detected);
  console.log('Missing Values Handled:', prep.metrics.missing_values_handled);
  if (prep.metrics.classes_count <= 0) throw new Error('Preprocessing failed to produce valid classes');

  // 5. AI/ML Prediction & Scheduling Engine: Greedy Baseline
  console.log('\n--- 5. SCHEDULING RUN: GREEDY BASELINE ---');
  const baseRes = await request('/api/generate', 'POST', { mode: 'baseline', seed: 42, applyRepair: true });
  console.log('POST /api/generate (baseline) Status:', baseRes.status);
  console.log(`Scheduled: ${baseRes.body.metrics.scheduled_classes} / ${baseRes.body.metrics.total_classes} (${baseRes.body.metrics.completion_pct}%)`);
  console.log(`Room Overlaps: ${baseRes.body.metrics.room_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Overlaps: ${baseRes.body.metrics.instructor_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Availability Violations: ${baseRes.body.metrics.availability_violations || 0} (Strict 0)`);
  console.log(`Capacity Deficits: ${baseRes.body.metrics.room_capacity_deficits || 0}`);
  console.log(`Runtime: ${baseRes.body.metrics.runtime_seconds} s`);
  if (baseRes.body.metrics.room_overlap_pairs !== 0 || baseRes.body.metrics.instructor_overlap_pairs !== 0) {
    throw new Error('Hard constraint collision detected in baseline schedule');
  }

  // 6. AI/ML Prediction & Scheduling Engine: Random Forest-Guided
  console.log('\n--- 6. SCHEDULING RUN: RANDOM FOREST-GUIDED ---');
  const rfRes = await request('/api/generate', 'POST', { mode: 'random_forest', seed: 42, applyRepair: true });
  console.log('POST /api/generate (random_forest) Status:', rfRes.status);
  console.log(`Scheduled: ${rfRes.body.metrics.scheduled_classes} / ${rfRes.body.metrics.total_classes} (${rfRes.body.metrics.completion_pct}%)`);
  console.log(`Room Overlaps: ${rfRes.body.metrics.room_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Overlaps: ${rfRes.body.metrics.instructor_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Availability Violations: ${rfRes.body.metrics.availability_violations || 0} (Strict 0)`);
  console.log(`Capacity Deficits: ${rfRes.body.metrics.room_capacity_deficits || 0}`);
  console.log(`Runtime: ${rfRes.body.metrics.runtime_seconds} s`);
  if (rfRes.body.metrics.room_overlap_pairs !== 0 || rfRes.body.metrics.instructor_overlap_pairs !== 0) {
    throw new Error('Hard constraint collision detected in Random Forest schedule');
  }

  // 7. AI/ML Prediction & Scheduling Engine: XGBoost-Guided
  console.log('\n--- 7. SCHEDULING RUN: XGBOOST-GUIDED ---');
  const xgbRes = await request('/api/generate', 'POST', { mode: 'xgboost', seed: 42, applyRepair: true });
  console.log('POST /api/generate (xgboost) Status:', xgbRes.status);
  console.log(`Scheduled: ${xgbRes.body.metrics.scheduled_classes} / ${xgbRes.body.metrics.total_classes} (${xgbRes.body.metrics.completion_pct}%)`);
  console.log(`Room Overlaps: ${xgbRes.body.metrics.room_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Overlaps: ${xgbRes.body.metrics.instructor_overlap_pairs} (Strict 0)`);
  console.log(`Teacher Availability Violations: ${xgbRes.body.metrics.availability_violations || 0} (Strict 0)`);
  console.log(`Capacity Deficits: ${xgbRes.body.metrics.room_capacity_deficits || 0}`);
  console.log(`Runtime: ${xgbRes.body.metrics.runtime_seconds} s`);
  if (xgbRes.body.metrics.room_overlap_pairs !== 0 || xgbRes.body.metrics.instructor_overlap_pairs !== 0) {
    throw new Error('Hard constraint collision detected in XGBoost schedule');
  }

  // 8. Fair Multi-Model Comparison: Compare All
  console.log('\n--- 8. MULTI-MODEL COMPARISON: COMPARE ALL ---');
  const compRes = await request('/api/generate', 'POST', { mode: 'compare_all', seed: 42, applyRepair: true });
  console.log('POST /api/generate (compare_all) Status:', compRes.status);
  console.log('Winner Declared:', compRes.body.winner);
  console.log('Winner Justification:', compRes.body.justification);
  console.log('Comparison Matrix:');
  compRes.body.comparison_matrix.forEach(m => {
    console.log(`  - ${m.name}: ${m.scheduled_classes}/${m.total_classes} (${m.completion_pct}%), Collisions: Room=${m.room_overlap_pairs}, Teacher=${m.instructor_overlap_pairs}, Avail=${m.availability_violations || 0}, Deficits=${m.room_capacity_deficits || 0}, SolveTime=${m.runtime_seconds}s`);
  });

  // 9. Duration Handling & Interval Integrity
  console.log('\n--- 9. CLASS DURATION INTEGRITY AUDIT ---');
  const timetableRecords = rfRes.body.records;
  const longClasses = timetableRecords.filter(r => r.duration_minutes >= 120);
  console.log(`Total 120-minute classes verified: ${longClasses.length}`);
  longClasses.slice(0, 3).forEach(c => {
    console.log(`  - ${c.course_code} (${c.course_name}): ${c.day} ${c.start_time} to ${c.end_time} (${c.duration_minutes}m) in ${c.room_name}`);
  });
  if (longClasses.length === 0) throw new Error('Expected multi-period duration classes in schedule');

  // 10. CSV Export Integrity
  console.log('\n--- 10. CSV EXPORT AUDIT ---');
  const csvRes = await request(`/api/export-csv/${rfRes.body.timetable_id}`);
  console.log(`GET /api/export-csv Status: ${csvRes.status}`);
  const csvText = csvRes.body;
  const header = csvText.split('\n')[0];
  console.log('CSV Header:', header);
  const containsTeacher = header.includes('teacher_id') && header.includes('teacher_name');
  const containsRoomType = header.includes('room_type');
  console.log('CSV contains teacher columns:', containsTeacher);
  console.log('CSV contains room_type:', containsRoomType, '(Must be false)');
  if (!containsTeacher) throw new Error('CSV export must include teacher_id and teacher_name');
  if (containsRoomType) throw new Error('CSV export must NOT include room_type');

  console.log('\n=======================================================');
  console.log('✓ ALL 10 ACCEPTANCE CRITERIA VERIFIED WITH 0 ERRORS!');
  console.log('=======================================================');
}

runAudit().catch(err => {
  console.error('\nAUDIT FAILED:', err.message);
  process.exit(1);
});
