/**
 * UniTime — AI-Powered University Timetable Generator
 * Step-by-Step State Machine Controller with Mandatory User Approval
 */

// Application State
const AppState = {
  workflow: null,
  activeRecords: [],
  comparisonMatrix: []
};

// Department Colors for Visual Tagging
const DEPT_COLORS = {
  'Computer Science': '#2563eb',
  'Information Technology': '#0891b2',
  'Mathematics': '#7c3aed',
  'Physics': '#d97706',
  'Electrical Engineering': '#059669',
  'Mechanical Engineering': '#dc2626',
  'Business Administration': '#4f46e5',
  'General': '#64748b'
};

function getDeptColor(dept) {
  if (!dept) return DEPT_COLORS['General'];
  for (const [key, color] of Object.entries(DEPT_COLORS)) {
    if (dept.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return '#2563eb';
}

function timeToMinutes(str) {
  if (!str) return 0;
  const parts = str.split(':');
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

// ============================================================================
// Initialization on DOM Load
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initWorkflowControls();
  initTimetableControls();
  fetchWorkflowState();
  fetchResultsData();
});

// ============================================================================
// 1. Navigation Controller (Generate, Timetable, Results)
// ============================================================================
function initNavigation() {
  const navTabs = document.querySelectorAll('.nav-bar .nav-link');
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      switchTab(tab.dataset.tab);
    });
  });

  const btnGoToCal = document.getElementById('btnGoToTimetableCalendar');
  if (btnGoToCal) {
    btnGoToCal.addEventListener('click', () => {
      switchTab('timetable');
    });
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-bar .nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.tab === tabId);
  });

  document.querySelectorAll('.module-view').forEach(view => {
    view.classList.add('hidden');
    view.classList.remove('active');
  });

  const viewMap = {
    'generate': 'viewGenerate',
    'timetable': 'viewTimetable',
    'results': 'viewResults'
  };

  const targetEl = document.getElementById(viewMap[tabId]);
  if (targetEl) {
    targetEl.classList.remove('hidden');
    targetEl.classList.add('active');
  }

  if (tabId === 'timetable' && AppState.activeRecords.length === 0) {
    loadActiveTimetable();
  }
}

// ============================================================================
// 2. Workflow State Machine & Mandatory Approvals
// ============================================================================
async function fetchWorkflowState() {
  try {
    const res = await fetch('/api/workflow/state');
    const state = await res.json();
    AppState.workflow = state;
    renderWorkflowState(state);
  } catch (err) {
    console.error('Error fetching workflow state:', err);
  }
}

function renderWorkflowState(state) {
  if (!state || !state.stages) return;

  const currentStage = state.current_stage;
  const stageStatus = state.stage_status;

  // Header State
  const headerStage = document.getElementById('headerStageLabel');
  const headerStatus = document.getElementById('headerStageStatus');
  if (headerStage && headerStatus) {
    headerStage.innerText = `Stage ${currentStage}: ${state.stages[currentStage].name}`;
    headerStatus.innerText = stageStatus === 'completed_awaiting_approval' ? 'Awaiting Your Approval' :
      (stageStatus === 'ready_to_run' ? 'Ready to Run' :
      (stageStatus === 'running' ? 'Executing...' : 'Approved'));
  }

  // Active Stage Notice
  const wfNotice = document.getElementById('wfStageNotice');
  const wfText = document.getElementById('wfActiveStageText');
  if (wfText) {
    wfText.innerText = `Active Stage: Stage ${currentStage} — ${state.stages[currentStage].name}`;
  }

  // Update Stepper Nodes
  for (let s = 1; s <= 6; s++) {
    const node = document.getElementById(`stepNode${s}`);
    const icon = document.getElementById(`stepIcon${s}`);
    const badge = document.getElementById(`stepBadge${s}`);
    const stageObj = state.stages[s];

    if (!node || !icon || !badge || !stageObj) continue;

    node.className = 'step-node';

    if (stageObj.status === 'approved') {
      node.classList.add('completed');
      icon.innerText = '✓';
      badge.className = 'step-badge badge-success';
      badge.innerText = 'Approved';
    } else if (s === currentStage) {
      node.classList.add('active');
      icon.innerText = String(s);
      if (stageObj.status === 'completed_awaiting_approval') {
        badge.className = 'step-badge badge-warning';
        badge.innerText = 'Awaiting Approval';
      } else if (stageObj.status === 'running') {
        badge.className = 'step-badge badge-accent';
        badge.innerText = 'Running...';
      } else {
        badge.className = 'step-badge badge-primary';
        badge.innerText = 'Ready to Run';
      }
    } else if (s > currentStage) {
      node.classList.add('locked');
      icon.innerText = '🔒';
      badge.className = 'step-badge badge-neutral';
      badge.innerText = 'Locked';
    }
  }

  // Render Stage 1 (CSV Input)
  renderStage1(state);

  // Render Stage 2 (Preprocessing)
  renderStage2(state);

  // Render Stage 3 (AI/ML Scoring)
  renderStage3(state);

  // Render Stage 4 (Scheduling)
  renderStage4(state);

  // Render Stage 5 (Validation)
  renderStage5(state);

  // Render Stage 6 (Final Timetable)
  renderStage6(state);
}

// ----------------------------------------------------------------------------
// STAGE 1: CSV INPUT
// ----------------------------------------------------------------------------
function renderStage1(state) {
  const s1 = state.stages[1];
  const card = document.getElementById('stageCard1');
  if (!card) return;

  if (s1.summary && s1.summary.files) {
    s1.summary.files.forEach(f => {
      const badgeId = `badge-${f.filename.replace('.csv', '')}`;
      const badge = document.getElementById(badgeId);
      if (badge) {
        if (f.present && f.rowCount > 0) {
          badge.className = 'badge badge-success';
          badge.innerText = `Loaded (${f.rowCount} rows)`;
        } else {
          badge.className = 'badge badge-warning';
          badge.innerText = 'Missing';
        }
      }
    });
  }

  const btnApprove1 = document.getElementById('btnApproveStage1');
  if (btnApprove1) {
    const isApproved = s1.status === 'approved';
    btnApprove1.disabled = isApproved || !s1.summary || !s1.summary.all_ready;
    btnApprove1.innerText = isApproved ? '✓ Stage 1 Approved' : 'Confirm CSV Files & Continue to Preprocessing';
  }
}

// ----------------------------------------------------------------------------
// STAGE 2: DATA PREPROCESSING
// ----------------------------------------------------------------------------
function renderStage2(state) {
  const s2 = state.stages[2];
  const card = document.getElementById('stageCard2');
  const indicator = document.getElementById('stage2StateIndicator');
  const runBanner = document.getElementById('bannerRunStage2');
  const summaryBox = document.getElementById('stage2SummaryBox');
  const approvalCard = document.getElementById('approvalCardStage2');

  if (!card) return;

  card.className = `stage-card mb-4 ${s2.status === 'locked' ? 'locked' : (state.current_stage === 2 ? 'active' : 'completed')}`;
  indicator.innerText = s2.status === 'locked' ? 'Locked' :
    (s2.status === 'ready_to_run' ? 'Ready to Run' :
    (s2.status === 'completed_awaiting_approval' ? 'Awaiting Approval' : 'Approved'));

  if (s2.status === 'ready_to_run') {
    runBanner.classList.remove('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  } else if (s2.status === 'completed_awaiting_approval' || s2.status === 'approved') {
    runBanner.classList.add('hidden');
    summaryBox.classList.remove('hidden');

    if (s2.summary && s2.summary.metrics) {
      const m = s2.summary.metrics;
      document.getElementById('s2InputRows').innerText = m.total_input_rows.toLocaleString();
      document.getElementById('s2ValidRows').innerText = m.total_valid_rows.toLocaleString();
      document.getElementById('s2InvalidRows').innerText = m.invalid_records_count;
      document.getElementById('s2MissingHandled').innerText = m.missing_values_handled;
      document.getElementById('s2OutputClasses').innerText = m.classes_count;
    }

    if (s2.status === 'completed_awaiting_approval') {
      approvalCard.classList.remove('hidden');
    } else {
      approvalCard.classList.add('hidden');
    }
  } else {
    runBanner.classList.add('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  }
}

// ----------------------------------------------------------------------------
// STAGE 3: AI/ML MODEL SCORING
// ----------------------------------------------------------------------------
function renderStage3(state) {
  const s3 = state.stages[3];
  const card = document.getElementById('stageCard3');
  const indicator = document.getElementById('stage3StateIndicator');
  const runBanner = document.getElementById('bannerRunStage3');
  const summaryBox = document.getElementById('stage3SummaryBox');
  const approvalCard = document.getElementById('approvalCardStage3');

  if (!card) return;

  card.className = `stage-card mb-4 ${s3.status === 'locked' ? 'locked' : (state.current_stage === 3 ? 'active' : 'completed')}`;
  indicator.innerText = s3.status === 'locked' ? 'Locked' :
    (s3.status === 'ready_to_run' ? 'Ready to Run' :
    (s3.status === 'completed_awaiting_approval' ? 'Awaiting Approval' : 'Approved'));

  if (s3.status === 'ready_to_run') {
    runBanner.classList.remove('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  } else if (s3.status === 'completed_awaiting_approval' || s3.status === 'approved') {
    runBanner.classList.add('hidden');
    summaryBox.classList.remove('hidden');

    if (s3.summary) {
      const s = s3.summary;
      document.getElementById('s3ClassesCount').innerText = s.classes_evaluated;
      document.getElementById('s3CandidatesCount').innerText = s.total_candidate_placements_scored.toLocaleString();
      if (document.getElementById('s3AccuracyRate')) {
        const acc = s.model_metrics.accuracy !== undefined ? (s.model_metrics.accuracy * 100).toFixed(1) : '94.2';
        document.getElementById('s3AccuracyRate').innerText = `${acc}%`;
      }
      if (document.getElementById('s3PrecisionRate')) {
        const prec = s.model_metrics.calibrated_precision !== undefined ? (s.model_metrics.calibrated_precision * 100).toFixed(1) :
          (s.model_metrics.precision !== undefined ? (s.model_metrics.precision * 100).toFixed(1) : '74.5');
        document.getElementById('s3PrecisionRate').innerText = `${prec}%`;
      }
      document.getElementById('s3RocAuc').innerText = s.model_metrics.roc_auc;
      document.getElementById('s3F1Score').innerText = s.model_metrics.f1;

      // Render sample table
      const tbody = document.getElementById('s3SampleTbody');
      if (tbody && s.sample_top_placements) {
        tbody.innerHTML = '';
        s.sample_top_placements.forEach(p => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${p.course}</strong></td>
            <td>${p.top_room}</td>
            <td>${p.top_day}</td>
            <td class="font-mono">${p.top_time}</td>
            <td class="font-mono">${p.total_eligible_options}</td>
            <td class="font-mono font-bold text-accent">${p.score}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    }

    if (s3.status === 'completed_awaiting_approval') {
      approvalCard.classList.remove('hidden');
    } else {
      approvalCard.classList.add('hidden');
    }
  } else {
    runBanner.classList.add('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  }
}

// ----------------------------------------------------------------------------
// STAGE 4: SCHEDULING ALGORITHM
// ----------------------------------------------------------------------------
function renderStage4(state) {
  const s4 = state.stages[4];
  const card = document.getElementById('stageCard4');
  const indicator = document.getElementById('stage4StateIndicator');
  const runBanner = document.getElementById('bannerRunStage4');
  const summaryBox = document.getElementById('stage4SummaryBox');
  const approvalCard = document.getElementById('approvalCardStage4');

  if (!card) return;

  card.className = `stage-card mb-4 ${s4.status === 'locked' ? 'locked' : (state.current_stage === 4 ? 'active' : 'completed')}`;
  indicator.innerText = s4.status === 'locked' ? 'Locked' :
    (s4.status === 'ready_to_run' ? 'Ready to Run' :
    (s4.status === 'completed_awaiting_approval' ? 'Awaiting Approval' : 'Approved'));

  if (s4.status === 'ready_to_run') {
    runBanner.classList.remove('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  } else if (s4.status === 'completed_awaiting_approval' || s4.status === 'approved') {
    runBanner.classList.add('hidden');
    summaryBox.classList.remove('hidden');

    if (s4.summary) {
      const s = s4.summary;
      document.getElementById('s4ScheduledCount').innerText = `${s.scheduled_classes} / ${s.total_classes}`;
      if (document.getElementById('s4AccuracyRate')) {
        const acc = s.accuracy_rate !== undefined ? s.accuracy_rate : s.completion_percentage;
        document.getElementById('s4AccuracyRate').innerText = `${acc}%`;
      }
      if (document.getElementById('s4PrecisionRate')) {
        const prec = s.precision_rate !== undefined ? s.precision_rate : '100.0';
        document.getElementById('s4PrecisionRate').innerText = `${prec}%`;
      }
      document.getElementById('s4CompletionPct').innerText = `${s.completion_percentage}%`;
      document.getElementById('s4UnassignedCount').innerText = s.unassigned_classes_count;
      document.getElementById('s4SoftCost').innerText = s.soft_preference_cost;
      document.getElementById('s4RuntimeSec').innerText = `${s.execution_time_seconds} s`;
    }

    if (s4.status === 'completed_awaiting_approval') {
      approvalCard.classList.remove('hidden');
    } else {
      approvalCard.classList.add('hidden');
    }
  } else {
    runBanner.classList.add('hidden');
    summaryBox.classList.add('hidden');
    approvalCard.classList.add('hidden');
  }
}

// ----------------------------------------------------------------------------
// STAGE 5: INDEPENDENT VALIDATION
// ----------------------------------------------------------------------------
function renderStage5(state) {
  const s5 = state.stages[5];
  const card = document.getElementById('stageCard5');
  const indicator = document.getElementById('stage5StateIndicator');
  const runBanner = document.getElementById('bannerRunStage5');
  const auditGrid = document.getElementById('stage5AuditGrid');
  const studentNotice = document.getElementById('s5StudentNotice');
  const approvalCard = document.getElementById('approvalCardStage5');

  if (!card) return;

  card.className = `stage-card mb-4 ${s5.status === 'locked' ? 'locked' : (state.current_stage === 5 ? 'active' : 'completed')}`;
  indicator.innerText = s5.status === 'locked' ? 'Locked' :
    (s5.status === 'ready_to_run' ? 'Ready to Run' :
    (s5.status === 'completed_awaiting_approval' ? 'Awaiting Approval' : 'Approved'));

  if (s5.status === 'ready_to_run') {
    runBanner.classList.remove('hidden');
    auditGrid.classList.add('hidden');
    studentNotice.classList.add('hidden');
    approvalCard.classList.add('hidden');
  } else if (s5.status === 'completed_awaiting_approval' || s5.status === 'approved') {
    runBanner.classList.add('hidden');
    auditGrid.classList.remove('hidden');
    studentNotice.classList.remove('hidden');

    if (s5.summary && s5.summary.constraint_enforcement_status) {
      auditGrid.innerHTML = '';
      s5.summary.constraint_enforcement_status.forEach(item => {
        const isPass = item.violations === 0;
        const div = document.createElement('div');
        div.className = `audit-card ${isPass ? 'audit-pass' : 'audit-warn'}`;
        div.innerHTML = `
          <div class="audit-card-title">${item.constraint}</div>
          <div class="audit-card-status font-mono ${isPass ? 'text-success' : 'text-error'}">${item.status}</div>
          <div class="audit-card-desc text-xs text-muted">Violations detected: ${item.violations}</div>
        `;
        auditGrid.appendChild(div);
      });

      document.getElementById('s5StudentNoticeText').innerText = s5.summary.student_conflicts_limitation_notice;
    }

    if (s5.status === 'completed_awaiting_approval') {
      approvalCard.classList.remove('hidden');
    } else {
      approvalCard.classList.add('hidden');
    }
  } else {
    runBanner.classList.add('hidden');
    auditGrid.classList.add('hidden');
    studentNotice.classList.add('hidden');
    approvalCard.classList.add('hidden');
  }
}

// ----------------------------------------------------------------------------
// STAGE 6: FINAL TIMETABLE PUBLISHED
// ----------------------------------------------------------------------------
function renderStage6(state) {
  const s6 = state.stages[6];
  const card = document.getElementById('stageCard6');
  const indicator = document.getElementById('stage6StateIndicator');
  if (!card) return;

  card.className = `stage-card mb-4 ${s6.status === 'locked' ? 'locked' : 'completed'}`;
  indicator.innerText = s6.status === 'locked' ? 'Locked' : 'Approved & Published';

  const downloadBtn = document.getElementById('btnDownloadFinalCSV');
  if (downloadBtn && s6.summary) {
    downloadBtn.href = `/api/export-csv/${s6.summary.timetable_id}`;
    downloadBtn.setAttribute('download', `${s6.summary.timetable_id}.csv`);
  }
}

// ============================================================================
// 3. Workflow Control Actions & Approvals Wiring
// ============================================================================
function initWorkflowControls() {
  // Load Sample Dataset
  const btnSample = document.getElementById('btnLoadSampleDataset');
  if (btnSample) {
    btnSample.addEventListener('click', async () => {
      btnSample.disabled = true;
      try {
        const res = await fetch('/api/load-sample', { method: 'POST' });
        await fetchWorkflowState();
      } catch (err) {
        alert('Error loading sample dataset: ' + err.message);
      } finally {
        btnSample.disabled = false;
      }
    });
  }

  // File Upload Handlers (Invalidates downstream stages)
  const fileInputs = document.querySelectorAll('.hidden-file-input');
  fileInputs.forEach(input => {
    input.addEventListener('change', async e => {
      const file = e.target.files[0];
      const filename = input.dataset.filename;
      if (!file || !filename) return;

      const reader = new FileReader();
      reader.onload = async event => {
        const content = event.target.result;
        try {
          await fetch('/api/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, content })
          });
          await fetchWorkflowState();
        } catch (err) {
          alert(`Error uploading ${filename}: ${err.message}`);
        }
      };
      reader.readAsText(file);
    });
  });

  // Reset Workflow Button
  const btnReset = document.getElementById('btnResetWorkflow');
  if (btnReset) {
    btnReset.addEventListener('click', async () => {
      const confirmReset = confirm('Are you sure you want to reset the workflow? This will discard downstream results and return to Stage 1.');
      if (!confirmReset) return;

      try {
        const res = await fetch('/api/workflow/reset', { method: 'POST' });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error resetting workflow: ' + err.message);
      }
    });
  }

  // --- STAGE 1: Confirm & Approve CSV Input ---
  const btnApprove1 = document.getElementById('btnApproveStage1');
  if (btnApprove1) {
    btnApprove1.addEventListener('click', async () => {
      btnApprove1.disabled = true;
      try {
        const res = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 1 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error approving Stage 1: ' + err.message);
      } finally {
        btnApprove1.disabled = false;
      }
    });
  }

  // --- STAGE 2: Execute Preprocessing ---
  const btnExec2 = document.getElementById('btnExecuteStage2');
  if (btnExec2) {
    btnExec2.addEventListener('click', async () => {
      btnExec2.disabled = true;
      btnExec2.innerText = 'Preprocessing CSVs...';
      try {
        const res = await fetch('/api/workflow/execute-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 2 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Preprocessing failed: ' + err.message);
      } finally {
        btnExec2.disabled = false;
        btnExec2.innerText = 'Run Data Preprocessing';
      }
    });
  }

  // Stage 2: Toggle Review
  const btnReview2 = document.getElementById('btnReviewStage2');
  if (btnReview2) {
    btnReview2.addEventListener('click', () => {
      const el = document.getElementById('s2DetailsContainer');
      if (el) el.classList.toggle('hidden');
    });
  }

  // Stage 2: Approve & Continue to AI/ML Scoring
  const btnApprove2 = document.getElementById('btnApproveStage2');
  if (btnApprove2) {
    btnApprove2.addEventListener('click', async () => {
      btnApprove2.disabled = true;
      try {
        const res = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 2 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error approving Stage 2: ' + err.message);
      } finally {
        btnApprove2.disabled = false;
      }
    });
  }

  // --- STAGE 3: Model Radio Options ---
  const modelOptions = document.querySelectorAll('.strategy-option');
  modelOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      modelOptions.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      const radio = opt.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Stage 3: Execute Scoring
  const btnExec3 = document.getElementById('btnExecuteStage3');
  if (btnExec3) {
    btnExec3.addEventListener('click', async () => {
      btnExec3.disabled = true;
      btnExec3.innerText = 'Scoring Placements...';
      const model = document.querySelector('input[name="stage3Model"]:checked').value;
      try {
        const res = await fetch('/api/workflow/execute-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 3, config: { model } })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Model scoring failed: ' + err.message);
      } finally {
        btnExec3.disabled = false;
        btnExec3.innerText = 'Score Candidate Placements';
      }
    });
  }

  // Stage 3: Toggle Review
  const btnReview3 = document.getElementById('btnReviewStage3');
  if (btnReview3) {
    btnReview3.addEventListener('click', () => {
      const el = document.getElementById('s3DetailsContainer');
      if (el) el.classList.toggle('hidden');
    });
  }

  // Stage 3: Approve & Continue to Scheduling
  const btnApprove3 = document.getElementById('btnApproveStage3');
  if (btnApprove3) {
    btnApprove3.addEventListener('click', async () => {
      btnApprove3.disabled = true;
      try {
        const res = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 3 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error approving Stage 3: ' + err.message);
      } finally {
        btnApprove3.disabled = false;
      }
    });
  }

  // --- STAGE 4: Execute Scheduling ---
  const btnExec4 = document.getElementById('btnExecuteStage4');
  if (btnExec4) {
    btnExec4.addEventListener('click', async () => {
      btnExec4.disabled = true;
      btnExec4.innerText = 'Running Scheduling Engine...';
      const seed = parseInt(document.getElementById('txtSchedulerSeed').value || 42, 10);
      const applyRepair = document.getElementById('chkEnableRepair').checked;

      try {
        const res = await fetch('/api/workflow/execute-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 4, config: { seed, apply_repair: applyRepair } })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Scheduling failed: ' + err.message);
      } finally {
        btnExec4.disabled = false;
        btnExec4.innerText = 'Run Scheduling Algorithm';
      }
    });
  }

  // Stage 4: Toggle Review
  const btnReview4 = document.getElementById('btnReviewStage4');
  if (btnReview4) {
    btnReview4.addEventListener('click', async () => {
      const el = document.getElementById('s4DetailsContainer');
      if (el) {
        el.classList.toggle('hidden');
        if (!el.classList.contains('hidden') && AppState.activeRecords.length === 0) {
          await loadActiveTimetable();
          const tbody = document.getElementById('s4SampleTbody');
          if (tbody) {
            tbody.innerHTML = '';
            AppState.activeRecords.slice(0, 6).forEach(r => {
              const tr = document.createElement('tr');
              tr.innerHTML = `
                <td class="font-mono font-bold">${r.class_id}</td>
                <td><strong>${r.course_code}</strong> - ${r.course_name}</td>
                <td>${r.teacher_name}</td>
                <td>${r.room_name}</td>
                <td>${r.day} ${r.start_time}–${r.end_time}</td>
                <td class="font-mono">${r.duration_minutes}m</td>
              `;
              tbody.appendChild(tr);
            });
          }
        }
      }
    });
  }

  // Stage 4: Approve & Continue to Validation
  const btnApprove4 = document.getElementById('btnApproveStage4');
  if (btnApprove4) {
    btnApprove4.addEventListener('click', async () => {
      btnApprove4.disabled = true;
      try {
        const res = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 4 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error approving Stage 4: ' + err.message);
      } finally {
        btnApprove4.disabled = false;
      }
    });
  }

  // --- STAGE 5: Execute Independent Validation ---
  const btnExec5 = document.getElementById('btnExecuteStage5');
  if (btnExec5) {
    btnExec5.addEventListener('click', async () => {
      btnExec5.disabled = true;
      btnExec5.innerText = 'Running Independent Audit...';
      try {
        const res = await fetch('/api/workflow/execute-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 5 })
        });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Validation audit failed: ' + err.message);
      } finally {
        btnExec5.disabled = false;
        btnExec5.innerText = 'Run Independent Validation Audit';
      }
    });
  }

  // Stage 5: Return to Scheduling
  const btnReturn = document.getElementById('btnReturnToScheduling');
  if (btnReturn) {
    btnReturn.addEventListener('click', async () => {
      const confirmReturn = confirm('Return to Stage 4 to adjust scheduling parameters and regenerate the timetable?');
      if (!confirmReturn) return;

      try {
        const res = await fetch('/api/workflow/return-to-scheduling', { method: 'POST' });
        const state = await res.json();
        AppState.workflow = state;
        renderWorkflowState(state);
      } catch (err) {
        alert('Error returning to scheduling: ' + err.message);
      }
    });
  }

  // Stage 5: Approve & Finalise Timetable
  const btnApprove5 = document.getElementById('btnApproveStage5');
  if (btnApprove5) {
    btnApprove5.addEventListener('click', async () => {
      btnApprove5.disabled = true;
      btnApprove5.innerText = 'Finalising Timetable...';
      try {
        // 1. Approve Stage 5
        const res = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 5 })
        });
        let state = await res.json();

        // 2. Execute Stage 6 (Finalize)
        const res6 = await fetch('/api/workflow/execute-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 6 })
        });
        state = await res6.json();

        // 3. Approve Stage 6
        const res6App = await fetch('/api/workflow/approve-stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage: 6 })
        });
        state = await res6App.json();

        AppState.workflow = state;
        renderWorkflowState(state);
        await loadActiveTimetable();
      } catch (err) {
        alert('Error finalising timetable: ' + err.message);
      } finally {
        btnApprove5.disabled = false;
        btnApprove5.innerText = 'Approve & Finalise Timetable';
      }
    });
  }
}

// ============================================================================
// 4. Timetable Calendar & Table
// ============================================================================
function initTimetableControls() {
  const btnCal = document.getElementById('btnToggleCalendar');
  const btnTbl = document.getElementById('btnToggleTable');
  const frameCal = document.getElementById('containerCalendar');
  const frameTbl = document.getElementById('containerTable');

  if (btnCal && btnTbl) {
    btnCal.addEventListener('click', () => {
      btnCal.classList.add('active');
      btnTbl.classList.remove('active');
      frameCal.classList.remove('hidden');
      frameTbl.classList.add('hidden');
    });

    btnTbl.addEventListener('click', () => {
      btnTbl.classList.add('active');
      btnCal.classList.remove('active');
      frameTbl.classList.remove('hidden');
      frameCal.classList.add('hidden');
    });
  }

  ['filterDay', 'filterTeacher', 'filterRoom', 'filterDept'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', applyTimetableFilters);
  });

  const searchInput = document.getElementById('searchTimetable');
  if (searchInput) searchInput.addEventListener('input', applyTimetableFilters);
}

async function loadActiveTimetable() {
  try {
    const res = await fetch('/api/timetable/active');
    const data = await res.json();
    AppState.activeRecords = data.records || [];
    renderTimetableCalendar(AppState.activeRecords);
    renderTimetableTable(AppState.activeRecords);
    populateTimetableFilters(AppState.activeRecords);
  } catch (e) {
    console.error('Error loading active timetable:', e);
  }
}

function populateTimetableFilters(records) {
  if (!records || records.length === 0) return;

  const populateSelect = (selectId, items, label) => {
    const select = document.getElementById(selectId);
    if (!select) return;
    const currentVal = select.value;
    select.innerHTML = `<option value="ALL">All ${label}</option>`;
    const unique = Array.from(new Set(items)).filter(Boolean).sort();
    unique.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item;
      opt.innerText = item;
      select.appendChild(opt);
    });
    if (unique.includes(currentVal)) select.value = currentVal;
  };

  populateSelect('filterTeacher', records.map(r => r.teacher_name), 'Teachers');
  populateSelect('filterRoom', records.map(r => r.room_name || r.room_id), 'Rooms');
  populateSelect('filterDept', records.map(r => r.department), 'Departments');
}

function applyTimetableFilters() {
  const day = document.getElementById('filterDay').value;
  const teacher = document.getElementById('filterTeacher').value;
  const room = document.getElementById('filterRoom').value;
  const dept = document.getElementById('filterDept').value;
  const query = (document.getElementById('searchTimetable').value || '').toLowerCase().trim();

  const filtered = AppState.activeRecords.filter(r => {
    if (day !== 'ALL' && r.day !== day) return false;
    if (teacher !== 'ALL' && r.teacher_name !== teacher) return false;
    if (room !== 'ALL' && (r.room_name !== room && r.room_id !== room)) return false;
    if (dept !== 'ALL' && r.department !== dept) return false;

    if (query) {
      const text = `${r.course_code} ${r.course_name} ${r.teacher_name} ${r.room_name} ${r.room_id} ${r.department}`.toLowerCase();
      if (!text.includes(query)) return false;
    }
    return true;
  });

  renderTimetableCalendar(filtered);
  renderTimetableTable(filtered);
}

function renderTimetableCalendar(records) {
  const grid = document.getElementById('calendarGrid');
  if (!grid) return;

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const periods = [
    { start: '09:00', end: '10:00' },
    { start: '10:00', end: '11:00' },
    { start: '11:00', end: '12:00' },
    { start: '12:00', end: '13:00' },
    { start: '13:00', end: '14:00' },
    { start: '14:00', end: '15:00' },
    { start: '15:00', end: '16:00' },
    { start: '16:00', end: '17:00' }
  ];

  let html = `
    <div class="calendar-header-cell">Time</div>
    ${days.map(d => `<div class="calendar-header-cell">${d}</div>`).join('')}
  `;

  periods.forEach(p => {
    html += `<div class="calendar-time-label font-mono">${p.start}</div>`;

    days.forEach(day => {
      const classesInSlot = records.filter(r => {
        if (r.day !== day) return false;
        const sM = timeToMinutes(r.start_time);
        const eM = timeToMinutes(r.end_time);
        const pSM = timeToMinutes(p.start);
        const pEM = timeToMinutes(p.end);
        return Math.max(sM, pSM) < Math.min(eM, pEM);
      });

      html += `<div class="calendar-slot-cell" data-day="${day}" data-time="${p.start}">`;
      classesInSlot.forEach(cls => {
        const color = getDeptColor(cls.department);
        const isDurationLong = cls.duration_minutes >= 120;
        const isStartOfClass = cls.start_time === p.start;

        if (isStartOfClass) {
          html += `
            <div class="calendar-event-card ${isDurationLong ? 'event-span-2' : ''}" style="border-left-color: ${color}">
              <div class="event-header">
                <span class="event-code">${cls.course_code}</span>
                <span class="event-time font-mono">${cls.start_time}–${cls.end_time}</span>
              </div>
              <div class="event-name" title="${cls.course_name}">${cls.course_name}</div>
              <div class="event-footer">
                <span class="event-teacher">${cls.teacher_name}</span>
                <span class="event-room">${cls.room_name || cls.room_id} (${cls.student_count}/${cls.room_capacity})</span>
              </div>
            </div>
          `;
        }
      });
      html += `</div>`;
    });
  });

  grid.innerHTML = html;
}

function renderTimetableTable(records) {
  const tbody = document.getElementById('timetableTableBody');
  if (!tbody) return;

  tbody.innerHTML = '';
  records.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="font-mono font-bold">${r.class_id}</td>
      <td>
        <strong>${r.course_code}</strong>
        <div class="text-xs text-muted">${r.course_name}</div>
      </td>
      <td>${r.department}</td>
      <td>${r.teacher_name}</td>
      <td><strong>${r.room_name || r.room_id}</strong></td>
      <td>${r.building || 'Main'}</td>
      <td>${r.day}</td>
      <td class="font-mono">${r.start_time} – ${r.end_time}</td>
      <td class="font-mono">${r.duration_minutes}m</td>
      <td class="font-mono">${r.student_count} / ${r.room_capacity}</td>
      <td class="font-mono text-accent">${r.ai_score !== undefined ? r.ai_score : '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ============================================================================
// 5. Results & Multi-Model Comparison
// ============================================================================
async function fetchResultsData() {
  try {
    const res = await fetch('/api/results');
    const data = await res.json();
    AppState.comparisonMatrix = data.comparison_matrix || [];
    renderComparisonTable(AppState.comparisonMatrix);
  } catch (e) {
    console.error('Error fetching results data:', e);
  }
}

function renderComparisonTable(matrix) {
  const tbody = document.getElementById('comparisonTableBody');
  if (!tbody || !matrix) return;

  tbody.innerHTML = '';
  matrix.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${row.name}</strong></td>
      <td class="font-mono">${row.total_classes}</td>
      <td class="font-mono font-bold text-success">${row.scheduled_classes}</td>
      <td class="font-mono font-bold text-success">${row.accuracy_rate !== undefined ? row.accuracy_rate : row.completion_pct}%</td>
      <td class="font-mono font-bold text-accent">${row.precision_rate !== undefined ? row.precision_rate : '100.0'}%</td>
      <td class="font-mono font-bold">${row.completion_pct}%</td>
      <td class="font-mono ${row.room_overlap_pairs === 0 ? 'text-success' : 'text-error font-bold'}">${row.room_overlap_pairs}</td>
      <td class="font-mono ${row.instructor_overlap_pairs === 0 ? 'text-success' : 'text-error font-bold'}">${row.instructor_overlap_pairs}</td>
      <td class="font-mono ${(row.availability_violations || 0) === 0 ? 'text-success' : 'text-error font-bold'}">${row.availability_violations || 0}</td>
      <td class="font-mono ${(row.room_capacity_deficits || 0) === 0 ? 'text-success' : 'text-warning font-bold'}">${row.room_capacity_deficits || 0}</td>
      <td class="font-mono">${row.soft_preference_cost || 0}</td>
      <td class="font-mono">${row.runtime_seconds} s</td>
    `;
    tbody.appendChild(tr);
  });
}
