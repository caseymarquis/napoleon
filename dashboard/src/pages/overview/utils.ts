import type { Project, Task } from './OverviewPageContract';

export const PROJECT_COLORS = ['#58a6ff', '#bc8cff', '#f0883e', '#3fb950', '#f778ba', '#79c0ff'];

export const DEFAULT_EST = 0.5;

export function colorFor(index: number): string {
	return PROJECT_COLORS[index % PROJECT_COLORS.length];
}

export function daysUntil(dateStr: string): number {
	const d = new Date(dateStr);
	d.setHours(0, 0, 0, 0);
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	return Math.ceil((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export function formatDate(dateStr: string): string {
	return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function resolveTaskStatus(
	task: Task,
	taskMap: Record<string, Task>,
): Task['status'] {
	if (task.status === 'completed') return 'completed';
	if (task.status === 'in_progress') return 'in_progress';
	const isBlocked = task.blockedBy.some((id) => {
		const blocker = taskMap[id];
		return blocker && blocker.status !== 'completed';
	});
	return isBlocked ? 'blocked' : task.status;
}

export function buildTaskMap(project: Project): Record<string, Task> {
	const m: Record<string, Task> = {};
	project.tasks.forEach((t) => (m[t.id] = t));
	return m;
}

export function getNextUp(project: Project): Task | null {
	const taskMap = buildTaskMap(project);
	const inProgress = project.tasks.find((t) => t.status === 'in_progress');
	if (inProgress) return inProgress;
	return project.tasks.find((t) => resolveTaskStatus(t, taskMap) === 'not_started') || null;
}

export function deadlineClass(days: number): string {
	return days <= 3 ? 'deadline-danger' : days <= 10 ? 'deadline-warn' : 'deadline-ok';
}

export interface ReadinessResult {
	score: number;
	grade: string;
	gradeClass: string;
	factors: { label: string; cls: string }[];
}

export function assessReadiness(project: Project): ReadinessResult {
	const factors: { label: string; cls: string }[] = [];
	let score = 100;

	const noEstimate = project.tasks.filter(
		(t) => t.est50 == null && t.status !== 'completed',
	).length;
	if (noEstimate > 0) {
		factors.push({ label: `${noEstimate} tasks unestimated`, cls: noEstimate > 2 ? 'bad' : 'warn' });
		score -= noEstimate * 8;
	}

	const notAtomic = project.tasks.filter(
		(t) => !t.atomic && t.status !== 'completed',
	).length;
	if (notAtomic > 0) {
		factors.push({ label: `${notAtomic} not yet atomic`, cls: notAtomic > 3 ? 'bad' : 'warn' });
		score -= notAtomic * 5;
	}

	const highRisk = project.tasks.filter(
		(t) => t.risk === 'high' && t.status !== 'completed',
	).length;
	if (highRisk > 0) {
		factors.push({ label: `${highRisk} high-risk`, cls: 'bad' });
		score -= highRisk * 12;
	}

	if (project.unknowns.length > 0) {
		factors.push({
			label: `${project.unknowns.length} unknowns`,
			cls: project.unknowns.length > 2 ? 'bad' : 'warn',
		});
		score -= project.unknowns.length * 10;
	}

	const unresolvedDeps = project.externalDeps.filter((d) => !d.resolved).length;
	if (unresolvedDeps > 0) {
		factors.push({ label: `${unresolvedDeps} ext deps pending`, cls: 'bad' });
		score -= unresolvedDeps * 15;
	}

	const completed = project.tasks.filter((t) => t.status === 'completed').length;
	if (completed > 0) {
		factors.push({ label: `${completed}/${project.tasks.length} done`, cls: 'ok' });
	}

	score = Math.max(0, Math.min(100, score));
	let grade: string, gradeClass: string;
	if (score >= 70) {
		grade = 'Well Defined';
		gradeClass = 'grade-well-defined';
	} else if (score >= 40) {
		grade = 'Partially Defined';
		gradeClass = 'grade-partial';
	} else {
		grade = 'Needs Detail';
		gradeClass = 'grade-needs-detail';
	}

	return { score, grade, gradeClass, factors };
}

export interface TimelineSegment {
	projectTitle: string;
	taskTitle: string;
	start: number;
	duration: number;
	risk: string;
	colorIndex: number;
}

export interface TimelineDeadline {
	title: string;
	day: number;
	date: string;
}

export function computeSequentialTimeline(projects: Project[]): {
	segments: TimelineSegment[];
	totalWork: number;
	deadlines: TimelineDeadline[];
	scaleMax: number;
} {
	// Sort by deadline for sequencing, but preserve original index for colors
	const withIndex = projects.map((p, i) => ({ project: p, colorIndex: i }));
	// Sequence work by priority, then deadline as tiebreaker
	const sorted = [...withIndex].sort((a, b) => {
		const pDiff = (a.project.priority ?? 99) - (b.project.priority ?? 99);
		if (pDiff !== 0) return pDiff;
		const aDate = a.project.deadline ? new Date(a.project.deadline).getTime() : Infinity;
		const bDate = b.project.deadline ? new Date(b.project.deadline).getTime() : Infinity;
		return aDate - bDate;
	});

	let dayOffset = 0;
	const segments: TimelineSegment[] = [];

	for (const { project, colorIndex } of sorted) {
		for (const task of project.tasks) {
			if (task.status === 'completed') continue;
			const dur = task.est50 || DEFAULT_EST;
			segments.push({
				projectTitle: project.title,
				taskTitle: task.title,
				start: dayOffset,
				duration: dur,
				risk: task.risk,
				colorIndex,
			});
			dayOffset += dur;
		}
	}

	const deadlines = projects
		.filter((p) => p.deadline)
		.map((p, _, arr) => ({
			title: p.title.split('\u2014')[0].trim(),
			day: daysUntil(p.deadline),
			date: p.deadline,
			colorIndex: projects.indexOf(p),
		}));

	// Scale hint: last real deadline + remaining work on that project
	let scaleMax = dayOffset;
	if (deadlines.length > 0) {
		const lastDeadline = Math.max(...deadlines.map((d) => d.day));
		const lastDlProject = [...projects]
			.filter((p) => p.deadline)
			.sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
			.at(-1);
		const lastProjectWork = lastDlProject
			? lastDlProject.tasks
					.filter((t) => t.status !== 'completed')
					.reduce((sum, t) => sum + (t.est50 || DEFAULT_EST), 0)
			: 0;
		scaleMax = lastDeadline + lastProjectWork;
	}

	return { segments, totalWork: dayOffset, deadlines, scaleMax };
}
