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

async function runStepByStepAudit() {
  console.log('====================================================================');
  console.log('AUDIT: STEP-BY-STEP EXECUTION WITH MANDATORY USER APPROVAL GATES');
  console.log('====================================================================');

  // 1. Reset workflow
  console.log('\n--- 1. WORKFLOW RESET & INITIAL STATE ---');
  const resetRes = await request('/api/workflow/reset', 'POST', { confirm: true });
  console.log('POST /api/workflow/reset Status:', resetRes.status);
  let state = resetRes.body;
  console.log('Current Stage:', state.current_stage, '(Must be 1)');
  console.log('Stage 1 Status:', state.stages[1].status);
  console.log('Stage 2 Status:', state.stages[2].status, '(Must be locked)');
  if (state.current_stage !== 1 || state.stages[2].status !== 'locked') {
    throw new Error('Initial state must have Stage 1 active and Stage 2 locked');
  }

  // 2. Test: Cannot bypass approval to execute Stage 2 directly
  console.log('\n--- 2. GUARD CHECK: CANNOT EXECUTE STAGE 2 WITHOUT STAGE 1 APPROVAL ---');
  const bypassRes = await request('/api/workflow/execute-stage', 'POST', { stage: 2 });
  console.log('Attempting to execute Stage 2 without Stage 1 approval -> Status:', bypassRes.status);
  console.log('Server Error Message:', bypassRes.body.error);
  if (bypassRes.status !== 400) {
    throw new Error('Server must reject Stage 2 execution before Stage 1 is approved');
  }

  // 3. Stage 1: Approve Stage 1
  console.log('\n--- 3. STAGE 1: CONFIRM CSV FILES & APPROVE ---');
  const app1 = await request('/api/workflow/approve-stage', 'POST', { stage: 1 });
  console.log('POST /api/workflow/approve-stage (Stage 1) -> Status:', app1.status);
  state = app1.body;
  console.log('Current Stage:', state.current_stage, '(Must be 2)');
  console.log('Stage 1 Status:', state.stages[1].status, '(Must be approved)');
  console.log('Stage 2 Status:', state.stages[2].status, '(Must be ready_to_run)');
  console.log('Stage 3 Status:', state.stages[3].status, '(Must be locked)');
  if (state.current_stage !== 2 || state.stages[2].status !== 'ready_to_run' || state.stages[3].status !== 'locked') {
    throw new Error('Stage 1 approval must advance workflow to Stage 2 ready_to_run, with Stage 3 locked');
  }

  // 4. Stage 2: Execute Preprocessing
  console.log('\n--- 4. STAGE 2: EXECUTE PREPROCESSING ONLY ---');
  const exec2 = await request('/api/workflow/execute-stage', 'POST', { stage: 2 });
  console.log('POST /api/workflow/execute-stage (Stage 2) -> Status:', exec2.status);
  state = exec2.body;
  console.log('Current Stage:', state.current_stage, '(Must stay 2)');
  console.log('Stage 2 Status:', state.stages[2].status, '(Must be completed_awaiting_approval)');
  console.log('Stage 3 Status:', state.stages[3].status, '(Must STILL be locked - NOT automatically executed!)');
  console.log('Preprocessing valid records:', state.stages[2].summary.metrics.total_valid_rows);
  if (state.stages[2].status !== 'completed_awaiting_approval' || state.stages[3].status !== 'locked') {
    throw new Error('Stage 2 execution must stop and await approval, keeping Stage 3 locked');
  }

  // 5. Test: Cannot bypass approval to execute Stage 3 directly
  console.log('\n--- 5. GUARD CHECK: CANNOT EXECUTE STAGE 3 WITHOUT STAGE 2 APPROVAL ---');
  const bypass3 = await request('/api/workflow/execute-stage', 'POST', { stage: 3 });
  console.log('Attempting to execute Stage 3 without Stage 2 approval -> Status:', bypass3.status);
  console.log('Server Error Message:', bypass3.body.error);
  if (bypass3.status !== 400) {
    throw new Error('Server must reject Stage 3 execution before Stage 2 is approved');
  }

  // 6. Stage 2: Approve & Continue to Stage 3
  console.log('\n--- 6. STAGE 2: APPROVE PREPROCESSING & ADVANCE TO STAGE 3 ---');
  const app2 = await request('/api/workflow/approve-stage', 'POST', { stage: 2 });
  state = app2.body;
  console.log('Current Stage:', state.current_stage, '(Must be 3)');
  console.log('Stage 2 Status:', state.stages[2].status, '(Must be approved)');
  console.log('Stage 3 Status:', state.stages[3].status, '(Must be ready_to_run)');
  console.log('Stage 4 Status:', state.stages[4].status, '(Must be locked)');
  if (state.current_stage !== 3 || state.stages[3].status !== 'ready_to_run' || state.stages[4].status !== 'locked') {
    throw new Error('Stage 2 approval must advance workflow to Stage 3 ready_to_run, with Stage 4 locked');
  }

  // 7. Stage 3: Execute AI/ML Model Scoring
  console.log('\n--- 7. STAGE 3: EXECUTE MODEL SCORING ONLY ---');
  const exec3 = await request('/api/workflow/execute-stage', 'POST', { stage: 3, config: { model: 'random_forest' } });
  state = exec3.body;
  console.log('POST /api/workflow/execute-stage (Stage 3) -> Status:', exec3.status);
  console.log('Current Stage:', state.current_stage, '(Must stay 3)');
  console.log('Stage 3 Status:', state.stages[3].status, '(Must be completed_awaiting_approval)');
  console.log('Stage 4 Status:', state.stages[4].status, '(Must STILL be locked - NOT automatically executed!)');
  console.log('Candidate placements scored:', state.stages[3].summary.total_candidate_placements_scored);
  console.log('ROC-AUC:', state.stages[3].summary.model_metrics.roc_auc);
  if (state.stages[3].status !== 'completed_awaiting_approval' || state.stages[4].status !== 'locked') {
    throw new Error('Stage 3 execution must stop and await approval, keeping Stage 4 locked');
  }

  // 8. Stage 3: Approve & Continue to Stage 4
  console.log('\n--- 8. STAGE 3: APPROVE MODEL SCORING & ADVANCE TO STAGE 4 ---');
  const app3 = await request('/api/workflow/approve-stage', 'POST', { stage: 3 });
  state = app3.body;
  console.log('Current Stage:', state.current_stage, '(Must be 4)');
  console.log('Stage 3 Status:', state.stages[3].status, '(Must be approved)');
  console.log('Stage 4 Status:', state.stages[4].status, '(Must be ready_to_run)');
  console.log('Stage 5 Status:', state.stages[5].status, '(Must be locked)');
  if (state.current_stage !== 4 || state.stages[4].status !== 'ready_to_run' || state.stages[5].status !== 'locked') {
    throw new Error('Stage 3 approval must advance workflow to Stage 4 ready_to_run, with Stage 5 locked');
  }

  // 9. Stage 4: Execute Scheduling Algorithm
  console.log('\n--- 9. STAGE 4: EXECUTE SCHEDULING ALGORITHM ONLY ---');
  const exec4 = await request('/api/workflow/execute-stage', 'POST', { stage: 4, config: { seed: 42, apply_repair: true } });
  state = exec4.body;
  console.log('POST /api/workflow/execute-stage (Stage 4) -> Status:', exec4.status);
  console.log('Current Stage:', state.current_stage, '(Must stay 4)');
  console.log('Stage 4 Status:', state.stages[4].status, '(Must be completed_awaiting_approval)');
  console.log('Stage 5 Status:', state.stages[5].status, '(Must STILL be locked - NOT automatically executed!)');
  console.log('Scheduled classes:', state.stages[4].summary.scheduled_classes, '/', state.stages[4].summary.total_classes);
  console.log('Completion percentage:', state.stages[4].summary.completion_percentage + '%');
  if (state.stages[4].status !== 'completed_awaiting_approval' || state.stages[5].status !== 'locked') {
    throw new Error('Stage 4 execution must stop and await approval, keeping Stage 5 locked');
  }

  // 10. Stage 4: Approve & Continue to Stage 5
  console.log('\n--- 10. STAGE 4: APPROVE SCHEDULE & ADVANCE TO STAGE 5 ---');
  const app4 = await request('/api/workflow/approve-stage', 'POST', { stage: 4 });
  state = app4.body;
  console.log('Current Stage:', state.current_stage, '(Must be 5)');
  console.log('Stage 4 Status:', state.stages[4].status, '(Must be approved)');
  console.log('Stage 5 Status:', state.stages[5].status, '(Must be ready_to_run)');
  console.log('Stage 6 Status:', state.stages[6].status, '(Must be locked)');
  if (state.current_stage !== 5 || state.stages[5].status !== 'ready_to_run' || state.stages[6].status !== 'locked') {
    throw new Error('Stage 4 approval must advance workflow to Stage 5 ready_to_run, with Stage 6 locked');
  }

  // 11. Stage 5: Execute Independent Validation
  console.log('\n--- 11. STAGE 5: EXECUTE INDEPENDENT VALIDATION AUDIT ONLY ---');
  const exec5 = await request('/api/workflow/execute-stage', 'POST', { stage: 5 });
  state = exec5.body;
  console.log('POST /api/workflow/execute-stage (Stage 5) -> Status:', exec5.status);
  console.log('Current Stage:', state.current_stage, '(Must stay 5)');
  console.log('Stage 5 Status:', state.stages[5].status, '(Must be completed_awaiting_approval)');
  console.log('Stage 6 Status:', state.stages[6].status, '(Must STILL be locked - NOT automatically finalized!)');
  console.log('Validation overall pass:', state.stages[5].summary.overall_pass);
  console.log('Room Collisions:', state.stages[5].summary.room_overlap_pairs_count);
  console.log('Teacher Collisions:', state.stages[5].summary.teacher_overlap_pairs_count);
  console.log('Teacher Availability Violations:', state.stages[5].summary.availability_violations_count);
  console.log('Capacity Deficits:', state.stages[5].summary.room_capacity_issues_count);
  if (state.stages[5].status !== 'completed_awaiting_approval' || state.stages[6].status !== 'locked') {
    throw new Error('Stage 5 execution must stop and await approval, keeping Stage 6 locked');
  }

  // 12. Stage 5: Approve & Finalise Timetable (Stage 6)
  console.log('\n--- 12. STAGE 5: APPROVE & FINALISE TIMETABLE (STAGE 6) ---');
  const app5 = await request('/api/workflow/approve-stage', 'POST', { stage: 5 });
  state = app5.body;
  console.log('Current Stage after Stage 5 approval:', state.current_stage, '(Must be 6)');
  console.log('Stage 6 Status:', state.stages[6].status, '(Must be ready_to_run)');

  // Execute Stage 6
  const exec6 = await request('/api/workflow/execute-stage', 'POST', { stage: 6 });
  state = exec6.body;
  console.log('Stage 6 Execution Status:', exec6.status);
  console.log('Final Timetable ID:', state.stages[6].summary.timetable_id);
  console.log('Final CSV Filename:', state.stages[6].summary.csv_filename);
  console.log('Final Scheduled Classes:', state.stages[6].summary.scheduled_classes);

  // Approve Stage 6
  const app6 = await request('/api/workflow/approve-stage', 'POST', { stage: 6 });
  state = app6.body;
  console.log('Workflow Final Status:', state.stage_status, '(Must be approved)');

  // 13. Test: Invalidation when a file is modified/uploaded
  console.log('\n--- 13. TEST: REPLACING AN INPUT FILE INVALIDATES DOWNSTREAM RESULTS ---');
  const sampleUpload = await request('/api/load-sample', 'POST', {});
  console.log('POST /api/load-sample Status:', sampleUpload.status);
  const reState = (await request('/api/workflow/state')).body;
  console.log('After file change, Current Stage:', reState.current_stage, '(Must reset to 1)');
  console.log('Stage 2 Status after file change:', reState.stages[2].status, '(Must be locked)');
  console.log('Stage 3 Status after file change:', reState.stages[3].status, '(Must be locked)');
  console.log('Stage 4 Status after file change:', reState.stages[4].status, '(Must be locked)');
  if (reState.current_stage !== 1 || reState.stages[2].status !== 'locked') {
    throw new Error('File change must invalidate downstream stages and reset back to Stage 1');
  }

  console.log('\n====================================================================');
  console.log('✓ ALL STEP-BY-STEP APPROVAL-GATE TESTS PASSED WITH 0 ERRORS!');
  console.log('====================================================================');
}

runStepByStepAudit().catch(err => {
  console.error('\nAUDIT FAILED:', err.message);
  process.exit(1);
});
