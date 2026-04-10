/* planning.js — Single-project focus: define the plan, validate estimates, surface gaps */

let selectedProjectId = loadState().selectedProjectId || null;

function renderPlanning(projects) {
  const el = document.getElementById('tab-planning');
  if (!projects.length) { el.innerHTML = '<div class="loading">No projects found.</div>'; return; }

  // Default to first project if none selected or selection is stale
  if (!selectedProjectId || !projects.find(p => p.id === selectedProjectId)) {
    selectedProjectId = projects[0].id;
    saveState({ selectedProjectId });
  }

  const project = projects.find(p => p.id === selectedProjectId);
  const taskMap = buildTaskMap(project);
  const days = daysUntil(project.deadline);
  const readiness = assessReadiness(project);
  const ordered = topoSort(project.tasks);

  const incomplete = project.tasks.filter(t => t.status !== 'completed');
  const total50 = incomplete.reduce((sum, t) => sum + (t.est50 || DEFAULT_EST), 0);
  const total90 = incomplete.reduce((sum, t) => sum + (t.est90 || DEFAULT_EST), 0);

  const criticalPath = computeCriticalPath(project.tasks, taskMap);

  // Gaps analysis
  const gaps = [];
  const unestimated = incomplete.filter(t => t.est50 == null);
  if (unestimated.length) gaps.push({ severity: 'warn', label: 'Unestimated tasks', items: unestimated.map(t => t.title) });

  const notAtomic = incomplete.filter(t => !t.atomic);
  if (notAtomic.length) gaps.push({ severity: 'warn', label: 'Not yet atomic (needs further breakdown)', items: notAtomic.map(t => t.title) });

  const partialEst = incomplete.filter(t => (t.est50 != null) !== (t.est90 != null));
  if (partialEst.length) gaps.push({ severity: 'warn', label: 'Partial estimates (missing 50 or 90)', items: partialEst.map(t => t.title) });

  const highRisk = incomplete.filter(t => t.risk === 'high');
  if (highRisk.length) gaps.push({ severity: 'bad', label: 'High-risk tasks (may blow estimates)', items: highRisk.map(t => t.title) });

  if (project.unknowns.length) gaps.push({ severity: 'warn', label: 'Open unknowns', items: project.unknowns });

  const unresolvedDeps = project.externalDeps.filter(d => !d.resolved);
  if (unresolvedDeps.length) gaps.push({ severity: 'bad', label: 'Unresolved external dependencies', items: unresolvedDeps.map(d => d.description) });

  const noDesc = project.tasks.filter(t => !t.description || t.description.length < 10);
  if (noDesc.length) gaps.push({ severity: 'warn', label: 'Tasks with thin descriptions', items: noDesc.map(t => t.title) });

  // Project selector
  const selector = projects.map(p =>
    `<button class="planning-project-btn ${p.id === selectedProjectId ? 'active' : ''}"
       onclick="selectProject('${p.id}')">${shortTitle(p.title)}</button>`
  ).join('');

  // Task detail rows
  const taskRows = ordered.map(t => {
    const resolved = resolveTaskStatus(t, taskMap);
    const isOnCriticalPath = criticalPath.has(t.id);
    return `<tr class="${isOnCriticalPath ? 'critical-path-row' : ''}">
      <td class="task-title-cell">
        ${isOnCriticalPath ? '<span class="critical-marker" title="Critical path">&#9679;</span> ' : ''}
        ${t.title}
        <div class="task-desc">${t.description}</div>
      </td>
      <td><span class="badge status-${resolved}">${statusLabel(resolved)}</span></td>
      <td class="est-cell"><input type="number" class="est-input" value="${t.est50 ?? ''}" step="0.25" min="0"
        placeholder="\u2013" onchange="updateTask('${project.id}', '${t.id}', {est50: this.value ? +this.value : null})" /></td>
      <td class="est-cell"><input type="number" class="est-input" value="${t.est90 ?? ''}" step="0.25" min="0"
        placeholder="\u2013" onchange="updateTask('${project.id}', '${t.id}', {est90: this.value ? +this.value : null})" /></td>
      <td><span class="risk-${t.risk}">${t.risk}</span></td>
      <td class="atomic-cell"><input type="checkbox" ${t.atomic ? 'checked' : ''}
        onchange="updateTask('${project.id}', '${t.id}', {atomic: this.checked})" /></td>
      <td>${t.blockedBy.map(id => {
        const dep = taskMap[id];
        return `<span class="blocker-tag">${dep ? dep.title.split('(')[0].trim() : id}</span>`;
      }).join('') || '\u2014'}</td>
    </tr>`;
  }).join('');

  // Gaps section
  const gapsHtml = gaps.length ? gaps.map(g => `
    <div class="gap-item gap-${g.severity}">
      <div class="gap-label">${g.label}</div>
      <ul>${g.items.map(i => `<li>${i}</li>`).join('')}</ul>
    </div>`).join('')
    : '<div style="color: var(--green); font-size: 0.85rem;">No major gaps identified.</div>';

  el.innerHTML = `
    <style>
      .planning-selector { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
      .planning-project-btn {
        padding: 0.4rem 1rem; border-radius: 6px; border: 1px solid var(--border);
        background: var(--surface); color: var(--text-muted); cursor: pointer;
        font-family: inherit; font-size: 0.85rem; font-weight: 500;
      }
      .planning-project-btn:hover { color: var(--text); border-color: var(--text-muted); }
      .planning-project-btn.active { color: var(--text); border-color: var(--accent); background: rgba(88, 166, 255, 0.08); }

      .planning-header {
        display: flex; justify-content: space-between; align-items: flex-start;
        margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);
      }
      .planning-header h2 { font-size: 1.25rem; font-weight: 600; }
      .planning-header-meta { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
      .planning-header-right { text-align: right; }

      .planning-stats {
        display: flex; gap: 1.5rem; margin-bottom: 1.5rem;
      }
      .planning-stat {
        background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
        padding: 1rem 1.25rem; flex: 1; text-align: center;
      }
      .planning-stat .value { font-size: 1.5rem; font-weight: 700; display: block; }
      .planning-stat .label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

      .planning-columns {
        display: grid; grid-template-columns: 1fr 350px; gap: 1.5rem; align-items: start;
      }

      .gap-item { margin-bottom: 0.75rem; padding: 0.75rem 1rem; border-radius: 6px; border-left: 3px solid; }
      .gap-warn { border-color: var(--yellow); background: rgba(210, 153, 34, 0.05); }
      .gap-bad { border-color: var(--red); background: rgba(248, 81, 73, 0.05); }
      .gap-label { font-weight: 600; font-size: 0.85rem; margin-bottom: 0.35rem; }
      .gap-item ul { list-style: none; font-size: 0.8rem; color: var(--text-muted); }
      .gap-item li { padding: 0.1rem 0; padding-left: 0.75rem; position: relative; }
      .gap-item li::before { content: "\\2013"; position: absolute; left: 0; }

      .critical-path-row { background: rgba(88, 166, 255, 0.04); }
      .critical-marker { color: var(--accent); font-size: 0.6rem; vertical-align: middle; }
      .atomic-marker { color: var(--green); font-size: 0.55rem; vertical-align: middle; }

      .est-cell { text-align: center; white-space: nowrap; width: 65px; }
      .est-input {
        width: 50px; padding: 0.2rem 0.3rem; text-align: center;
        background: var(--bg); border: 1px solid var(--border-light); border-radius: 4px;
        color: var(--text); font-size: 0.8rem; font-family: inherit;
        transition: border-color 0.15s;
      }
      .est-input:focus { outline: none; border-color: var(--accent); }
      .est-input::placeholder { color: var(--text-dim); }
      .est-input::-webkit-inner-spin-button,
      .est-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
      .est-input { -moz-appearance: textfield; }
      .atomic-cell { text-align: center; }
      .atomic-cell input[type="checkbox"] { cursor: pointer; width: 15px; height: 15px; accent-color: var(--green); }
    </style>

    <div class="planning-selector">${selector}</div>

    <div class="planning-header">
      <div>
        <h2>${project.title}</h2>
        <div class="planning-header-meta">
          ${project.description}<br>
          Committed to: ${project.committedTo} &middot; Status: ${project.status}
        </div>
      </div>
      <div class="planning-header-right">
        <span class="deadline-badge ${deadlineClass(days)}">${formatDate(project.deadline)} (${days}d remaining)</span>
        <div style="margin-top: 0.5rem;">
          <span class="readiness-grade ${readiness.gradeClass}" style="padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">${readiness.grade}</span>
        </div>
      </div>
    </div>

    <div class="planning-stats">
      <div class="planning-stat">
        <span class="value">${project.tasks.length}</span>
        <span class="label">Tasks</span>
      </div>
      <div class="planning-stat">
        <span class="value" style="color: ${total50 > days ? 'var(--red)' : 'var(--green)'}">${total50}d</span>
        <span class="label">Total (50%)</span>
      </div>
      <div class="planning-stat">
        <span class="value" style="color: ${total90 > days ? 'var(--red)' : 'var(--green)'}">${total90}d</span>
        <span class="label">Total (90%)</span>
      </div>
      <div class="planning-stat">
        <span class="value">${criticalPath.size}</span>
        <span class="label">Critical Path</span>
      </div>
      <div class="planning-stat">
        <span class="value">${unestimated.length}</span>
        <span class="label">Unestimated</span>
      </div>
    </div>

    <div class="planning-columns">
      <div>
        <div class="section-title">Tasks (dependency order)</div>
        <table class="task-table planning-task-table">
          <thead><tr><th>Task</th><th>Status</th><th>50%</th><th>90%</th><th>Risk</th><th>Atomic</th><th>Blocked By</th></tr></thead>
          <tbody>${taskRows}</tbody>
        </table>

        ${project.minimumDelivery ? `<div class="min-delivery" style="margin-top: 1.5rem;"><strong>Minimum delivery:</strong> ${project.minimumDelivery}</div>` : ''}
      </div>

      <div>
        <div class="panel" style="margin-bottom: 1rem;">
          <div class="panel-title">Gaps &amp; Attention Needed</div>
          ${gapsHtml}
        </div>

        ${project.unknowns.length ? `
        <div class="panel" style="margin-bottom: 1rem;">
          <div class="panel-title">Unknowns</div>
          <ul class="info-panel-list">${project.unknowns.map(u => `<li style="font-size: 0.85rem; padding: 0.2rem 0; color: var(--yellow);">\u25CB ${u}</li>`).join('')}</ul>
        </div>` : ''}

        ${project.externalDeps.length ? `
        <div class="panel" style="margin-bottom: 1rem;">
          <div class="panel-title">External Dependencies</div>
          <ul style="list-style: none; font-size: 0.85rem;">${project.externalDeps.map(d =>
            `<li style="padding: 0.2rem 0;" class="${d.resolved ? 'dep-resolved' : 'dep-pending'}">${d.resolved ? '\u2713' : '\u25CB'} ${d.description}</li>`
          ).join('')}</ul>
        </div>` : ''}

        ${project.constraints.length ? `
        <div class="panel">
          <div class="panel-title">Constraints</div>
          <ul style="list-style: none; font-size: 0.85rem;">${project.constraints.map(c =>
            `<li style="padding: 0.2rem 0; color: var(--text-muted);">\u2022 ${c}</li>`
          ).join('')}</ul>
        </div>` : ''}
      </div>
    </div>`;
}

async function updateTask(projectId, taskId, updates) {
  await fetch('/api/task/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phash: PROJECT_HASH, project: projectId, task: taskId, updates })
  });
}

function selectProject(id) {
  selectedProjectId = id;
  saveState({ selectedProjectId });
  renderPlanning(projects);
}

function computeCriticalPath(tasks, taskMap) {
  const memo = {};
  function longestFrom(taskId) {
    if (memo[taskId] != null) return memo[taskId];
    const task = taskMap[taskId];
    if (!task) return { length: 0, path: [] };

    let maxDep = { length: 0, path: [] };
    for (const depId of task.blockedBy) {
      const dep = longestFrom(depId);
      if (dep.length > maxDep.length) maxDep = dep;
    }

    const dur = task.status === 'completed' ? 0 : (task.est50 || DEFAULT_EST);
    memo[taskId] = { length: maxDep.length + dur, path: [...maxDep.path, taskId] };
    return memo[taskId];
  }

  let longest = { length: 0, path: [] };
  for (const t of tasks) {
    const result = longestFrom(t.id);
    if (result.length > longest.length) longest = result;
  }

  return new Set(longest.path);
}
