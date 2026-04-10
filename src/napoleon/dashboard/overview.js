/* overview.js — High-level dashboard: capacity, next-up, readiness, project summaries */

function computeSequentialTimeline(projects) {
  const sorted = [...projects].sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
  let dayOffset = 0;
  const segments = [];

  for (let pi = 0; pi < sorted.length; pi++) {
    const project = sorted[pi];
    const ordered = topoSort(project.tasks);
    for (const task of ordered) {
      if (task.status === 'completed') continue;
      const dur = task.est50 || DEFAULT_EST;
      segments.push({
        projectTitle: project.title,
        taskTitle: task.title,
        start: dayOffset,
        duration: dur,
        risk: task.risk,
        colorIndex: pi
      });
      dayOffset += dur;
    }
  }

  const deadlines = sorted.map(p => ({
    title: p.title,
    day: daysUntil(p.deadline),
    date: p.deadline
  }));

  return { segments, totalWork: dayOffset, deadlines };
}

function getNextUp(project) {
  const taskMap = buildTaskMap(project);
  const inProgress = project.tasks.find(t => t.status === 'in_progress');
  if (inProgress) return inProgress;
  return project.tasks.find(t => resolveTaskStatus(t, taskMap) === 'not_started') || null;
}

function renderOverview(projects) {
  const el = document.getElementById('tab-overview');
  if (!projects.length) { el.innerHTML = '<div class="loading">No projects found.</div>'; return; }

  const timeline = computeSequentialTimeline(projects);
  const maxDay = Math.max(timeline.totalWork, ...timeline.deadlines.map(d => d.day));
  const scale = maxDay > 0 ? 100 / maxDay : 100;
  const latestDeadline = Math.max(...timeline.deadlines.map(d => d.day));
  const overBy = timeline.totalWork - latestDeadline;
  const capacityClass = overBy > 5 ? 'over' : overBy > 0 ? 'tight' : 'ok';

  const barSegments = timeline.segments.map(s =>
    `<div class="capacity-bar-segment" style="
       left: ${s.start * scale}%; width: ${Math.max(s.duration * scale, 0.5)}%;
       background: ${PROJECT_COLORS[s.colorIndex % PROJECT_COLORS.length]};
       opacity: ${s.risk === 'high' ? 0.9 : s.risk === 'medium' ? 0.7 : 0.5};
     " title="${s.projectTitle}: ${s.taskTitle} (${s.duration}d)"></div>`
  ).join('');

  const deadlineMarkers = timeline.deadlines.map((d, i) =>
    `<div class="capacity-deadline-marker" style="left: ${d.day * scale}%;
       background: ${PROJECT_COLORS[i % PROJECT_COLORS.length]};">
       <div class="capacity-deadline-label" style="color: ${PROJECT_COLORS[i % PROJECT_COLORS.length]}">
         ${shortTitle(d.title)} ${formatDate(d.date)}
       </div></div>`
  ).join('');

  const sorted = [...projects].sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
  const legend = sorted.map((p, i) =>
    `<span><span style="background: ${PROJECT_COLORS[i % PROJECT_COLORS.length]}; display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: middle;"></span>${shortTitle(p.title)}</span>`
  ).join('');

  const nextUpItems = projects.map((p, i) => {
    const next = getNextUp(p);
    if (!next) return `
      <div class="next-up-item" style="border-left-color: ${PROJECT_COLORS[i % PROJECT_COLORS.length]}">
        <div class="next-up-project">${p.title}</div>
        <div class="next-up-task" style="color: var(--green)">All tasks complete</div>
      </div>`;
    return `
      <div class="next-up-item" style="border-left-color: ${PROJECT_COLORS[i % PROJECT_COLORS.length]}">
        <div class="next-up-project">${p.title}</div>
        <div class="next-up-task">${next.title}</div>
        <div class="next-up-desc">${next.description}</div>
        <div class="next-up-risk">Risk: <span class="risk-${next.risk}">${next.risk}</span></div>
      </div>`;
  }).join('');

  const readinessItems = projects.map(p => {
    const r = assessReadiness(p);
    const days = daysUntil(p.deadline);
    return `
      <div class="readiness-item">
        <div class="readiness-header">
          <span class="readiness-project">${shortTitle(p.title)}</span>
          <span class="readiness-grade ${r.gradeClass}">${r.grade}</span>
        </div>
        <div class="readiness-factors">
          ${r.factors.map(f => `<span class="readiness-factor ${f.cls}">${f.label}</span>`).join('')}
          <span class="readiness-factor ${days <= 3 ? 'bad' : days <= 10 ? 'warn' : 'ok'}">${days}d left</span>
        </div>
      </div>`;
  }).join('');

  // Collapsible project details
  const projectCards = projects.map((p, i) => {
    const taskMap = buildTaskMap(p);
    const days = daysUntil(p.deadline);
    const statusCounts = { not_started: 0, in_progress: 0, completed: 0, blocked: 0 };
    p.tasks.forEach(t => { statusCounts[resolveTaskStatus(t, taskMap)]++; });
    return `
      <div class="project" id="project-${p.id}">
        <div class="project-header" onclick="toggleProject('${p.id}')">
          <div class="project-header-left">
            <span class="project-toggle" id="toggle-${p.id}">\u25B6</span>
            <span class="project-title">${p.title}</span>
            <span class="project-meta">
              <span>${statusCounts.completed}/${p.tasks.length} done</span>
              <span>${p.committedTo}</span>
            </span>
          </div>
          <span class="deadline-badge ${deadlineClass(days)}">${formatDate(p.deadline)} (${days}d)</span>
        </div>
        <div class="project-body" id="body-${p.id}">
          <div class="info-row">
            ${p.unknowns.length ? `<div class="info-panel"><h3>Unknowns</h3><ul>${p.unknowns.map(u => `<li>${u}</li>`).join('')}</ul></div>` : ''}
            ${p.constraints.length ? `<div class="info-panel"><h3>Constraints</h3><ul>${p.constraints.map(c => `<li>${c}</li>`).join('')}</ul></div>` : ''}
            ${p.externalDeps.length ? `<div class="info-panel"><h3>External Dependencies</h3><ul>${p.externalDeps.map(d =>
              `<li class="${d.resolved ? 'dep-resolved' : 'dep-pending'}">${d.description}${d.resolved ? ` (resolved ${formatDate(d.resolvedDate)})` : ''}</li>`
            ).join('')}</ul></div>` : ''}
          </div>
          <div class="section-title">Tasks</div>
          <table class="task-table">
            <thead><tr><th>Task</th><th>Status</th><th>Risk</th><th>Blocked By</th></tr></thead>
            <tbody>${p.tasks.map(t => {
              const resolved = resolveTaskStatus(t, taskMap);
              return `<tr>
                <td class="task-title-cell">${t.title}<div class="task-desc">${t.description}</div></td>
                <td><span class="badge status-${resolved}">${statusLabel(resolved)}</span></td>
                <td><span class="risk-${t.risk}">${t.risk}</span></td>
                <td>${t.blockedBy.map(id => { const dep = taskMap[id]; return `<span class="blocker-tag">${dep ? dep.title.split('(')[0].trim() : id}</span>`; }).join('') || '\u2014'}</td>
              </tr>`;
            }).join('')}</tbody>
          </table>
          ${p.minimumDelivery ? `<div class="min-delivery"><strong>Minimum delivery:</strong> ${p.minimumDelivery}</div>` : ''}
        </div>
      </div>`;
  }).join('');

  el.innerHTML = `
    <div class="command-center">
      <div class="panel command-center-full">
        <div class="panel-title">Sequential Capacity (single-threaded)</div>
        <div class="capacity-summary">
          <div class="capacity-stat ${capacityClass}"><span class="value">${timeline.totalWork}d</span><span class="label">total work (estimated)</span></div>
          <div class="capacity-stat"><span class="value">${latestDeadline}d</span><span class="label">until last deadline</span></div>
          <div class="capacity-stat ${capacityClass}"><span class="value">${overBy > 0 ? '+' + overBy + 'd' : 'OK'}</span><span class="label">${overBy > 0 ? 'over capacity' : 'fits in window'}</span></div>
        </div>
        <div class="capacity-bar-container">${barSegments}${deadlineMarkers}</div>
        <div class="capacity-legend">${legend}</div>
      </div>
      <div class="panel"><div class="panel-title">Next Up (per project)</div><div class="next-up-list">${nextUpItems}</div></div>
      <div class="panel"><div class="panel-title">Project Readiness</div><div class="readiness-list">${readinessItems}</div></div>
    </div>
    <div class="details-header">Project Details</div>
    ${projectCards}`;

  // Restore expanded state
  (renderOverview._open || []).forEach(id => {
    const body = document.getElementById('body-' + id);
    const toggle = document.getElementById('toggle-' + id);
    if (body) body.classList.add('open');
    if (toggle) toggle.classList.add('open');
  });
}

renderOverview._open = [];

function toggleProject(id) {
  const body = document.getElementById('body-' + id);
  const toggle = document.getElementById('toggle-' + id);
  const isOpen = body.classList.toggle('open');
  toggle.classList.toggle('open', isOpen);

  // Track state for re-renders
  const set = new Set(renderOverview._open);
  if (isOpen) set.add(id); else set.delete(id);
  renderOverview._open = [...set];
}
