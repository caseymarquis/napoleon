<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { computeSequentialTimeline, computeProjectBuffer, colorFor, formatDate, DEFAULT_EST } from './utils';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Gantt, WillowDark } from '@svar-ui/svelte-gantt';
	import GanttTaskBar from './GanttTaskBar.svelte';

	export type TaskKey = { projectId: string; taskId: string } | null;

	let {
		projects,
		selectedTaskKey = $bindable(null),
	}: {
		projects: Project[];
		selectedTaskKey?: TaskKey;
	} = $props();

	let timeline = $derived(computeSequentialTimeline(projects));
	let deadlineDays = $derived(timeline.deadlines.map((d) => d.day));
	let latestDeadline = $derived(deadlineDays.length > 0 ? Math.max(...deadlineDays) : 0);
	let totalBuffer = $derived(timeline.buffers.reduce((sum, b) => sum + b.buffer, 0));
	// Compare work + buffer against deadline
	let overBy = $derived(
		latestDeadline > 0
			? Math.round((timeline.totalWithBuffers - latestDeadline) * 10) / 10
			: 0,
	);
	let capacityStatus = $derived<'over' | 'tight' | 'ok'>(
		overBy > 5 ? 'over' : overBy > 0 ? 'tight' : 'ok',
	);

	const statusStyle: Record<'over' | 'tight' | 'ok', string> = {
		over: 'text-destructive-foreground',
		tight: 'text-chart-4',
		ok: 'text-chart-2',
	};

	// Stable numeric ID from string — same string always produces the same ID
	function stableId(s: string): number {
		let hash = 5381;
		for (let i = 0; i < s.length; i++) hash = ((hash << 5) + hash + s.charCodeAt(i)) | 0;
		return Math.abs(hash);
	}

	// Build gantt tasks at individual task level, grouped under project summaries
	let ganttTasks = $derived.by(() => {
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const tasks: any[] = [];
		let dayOffset = 0;

		const sorted = [...projects].sort((a, b) => {
			const pDiff = (a.priority ?? 99) - (b.priority ?? 99);
			if (pDiff !== 0) return pDiff;
			const aDate = a.deadline ? new Date(a.deadline).getTime() : Infinity;
			const bDate = b.deadline ? new Date(b.deadline).getTime() : Infinity;
			return aDate - bDate;
		});

		for (const project of sorted) {
			const remaining = project.tasks.filter((t) => t.status !== 'completed');
			if (remaining.length === 0) continue;

			const projectGanttId = stableId(`project:${project.id}`);
			const projectStart = dayOffset;

			// Individual tasks
			for (const task of remaining) {
				const dur = task.est50 || DEFAULT_EST;
				const start = new Date(today);
				start.setDate(start.getDate() + Math.round(dayOffset));
				const end = new Date(today);
				end.setDate(end.getDate() + Math.round(dayOffset + dur));

				tasks.push({
					id: stableId(`task:${project.id}:${task.id}`),
					text: task.title,
					start,
					end,
					duration: Math.max(Math.round(dur), 1),
					progress: 0,
					type: 'task',
					parent: projectGanttId,
					// Extra metadata for click/tooltip/editing
					_projectId: project.id,
					_taskId: task.id,
					_risk: task.risk,
					_est50: task.est50,
					_est90: task.est90,
					_description: task.description,
					_atomic: task.atomic,
					_status: task.status,
				});

				dayOffset += dur;
			}

			// Buffer row (CCPM: sqrt of sum of squared differences between est90 and est50)
			const bufferInfo = timeline.buffers.find((b) => b.projectId === project.id);
			if (bufferInfo && bufferInfo.buffer > 0) {
				const bufStart = new Date(today);
				bufStart.setDate(bufStart.getDate() + Math.round(dayOffset));
				const bufEnd = new Date(today);
				bufEnd.setDate(bufEnd.getDate() + Math.round(dayOffset + bufferInfo.buffer));

				tasks.push({
					id: stableId(`buffer:${project.id}`),
					text: `Buffer (${bufferInfo.buffer}d)`,
					start: bufStart,
					end: bufEnd,
					duration: Math.max(Math.round(bufferInfo.buffer), 1),
					progress: 0,
					type: 'task',
					parent: projectGanttId,
					_projectId: project.id,
					_isBuffer: true,
				});

				dayOffset += bufferInfo.buffer;
			}

			// Project summary (parent) — spans tasks + buffer
			const projectEnd = new Date(today);
			projectEnd.setDate(projectEnd.getDate() + Math.round(dayOffset));
			const projectStartDate = new Date(today);
			projectStartDate.setDate(projectStartDate.getDate() + Math.round(projectStart));

			tasks.push({
				id: projectGanttId,
				text: project.title,
				start: projectStartDate,
				end: projectEnd,
				duration: Math.round(dayOffset - projectStart),
				progress: 0,
				type: 'summary',
				open: true,
				_projectId: project.id,
			});
		}

		// Buffer row at the end
		tasks.push({
			id: stableId('buffer'),
			text: '',
			start: new Date(today),
			end: new Date(today),
			duration: 0,
			progress: 0,
			type: 'task',
		});

		return tasks;
	});

	// Sequential links between individual tasks
	let ganttLinks = $derived.by(() => {
		const taskItems = ganttTasks.filter((t) => t.type === 'task');
		return taskItems.slice(1).map((t, i) => ({
			id: i + 1,
			source: taskItems[i].id,
			target: t.id,
			type: 'e2e',
		}));
	});

	let ganttScales = [
		{ unit: 'week', step: 1, format: '%d %M' },
		{ unit: 'day', step: 1, format: '%d' },
	];

	// Date range: today to end of work + buffer
	let ganttStart = $derived.by(() => {
		const d = new Date();
		d.setHours(0, 0, 0, 0);
		d.setDate(d.getDate() - 1);
		return d;
	});

	let ganttEnd = $derived.by(() => {
		const d = new Date();
		d.setHours(0, 0, 0, 0);
		d.setDate(d.getDate() + Math.round(timeline.scaleMax) + 7);
		return d;
	});

	// Track task keys we've seen (non-reactive). When a new one appears
	// (created via CLI or UI), auto-focus it so it's editable immediately.
	let seenTaskKeys: Set<string> | null = null;

	$effect(() => {
		const currentKeys = new Set<string>();
		const newTasks: { projectId: string; taskId: string }[] = [];
		for (const t of ganttTasks) {
			if (t.type !== 'task' || t._isBuffer || !t._taskId) continue;
			const key = `${t._projectId}:${t._taskId}`;
			currentKeys.add(key);
			if (seenTaskKeys && !seenTaskKeys.has(key)) {
				newTasks.push({ projectId: t._projectId, taskId: t._taskId });
			}
		}
		// First render: just record, don't auto-focus
		if (seenTaskKeys === null) {
			seenTaskKeys = currentKeys;
			return;
		}
		// New tasks appeared — focus the last one
		if (newTasks.length > 0) {
			selectedTaskKey = newTasks[newTasks.length - 1];
		}
		seenTaskKeys = currentKeys;
	});

	function ganttInit(api: any) {
		api.on('select-task', (ev: any) => {
			const task = ganttTasks.find((t) => t.id === ev.id);
			if (!task || task.text === '') return;
			selectedTaskKey = { projectId: task._projectId, taskId: task._taskId };
		});
	}
</script>

<Card.Root>
	<Card.Header>
		<Card.Title class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
			Sequential Capacity (single-threaded)
		</Card.Title>
	</Card.Header>
	<Card.Content>
		<!-- Stats -->
		<div class="mb-5 flex gap-10">
			<div class="flex flex-col">
				<span class="text-2xl font-bold leading-tight">
					{timeline.totalWork}d
				</span>
				<span class="mt-0.5 text-xs text-muted-foreground">work (est50)</span>
			</div>
			<div class="flex flex-col">
				<span class="text-2xl font-bold leading-tight text-muted-foreground">
					+{totalBuffer}d
				</span>
				<span class="mt-0.5 text-xs text-muted-foreground">buffer (CCPM)</span>
			</div>
			<div class="flex flex-col">
				<span class="text-2xl font-bold leading-tight {statusStyle[capacityStatus]}">
					{timeline.totalWithBuffers}d
				</span>
				<span class="mt-0.5 text-xs text-muted-foreground">total with buffer</span>
			</div>
			<div class="flex flex-col">
				<span class="text-2xl font-bold leading-tight">{latestDeadline}d</span>
				<span class="mt-0.5 text-xs text-muted-foreground">until last deadline</span>
			</div>
			<div class="flex flex-col">
				<span class="text-2xl font-bold leading-tight {statusStyle[capacityStatus]}">
					{overBy > 0 ? `+${overBy}d` : 'OK'}
				</span>
				<span class="mt-0.5 text-xs text-muted-foreground">
					{overBy > 0 ? 'over capacity' : 'fits in window'}
				</span>
			</div>
		</div>

		<!-- Gantt -->
		{#if ganttTasks.length > 0}
			<div class="max-h-96 overflow-auto rounded-md border border-border">
				<WillowDark>
					<Gantt
						init={ganttInit}
						tasks={ganttTasks}
						links={[]}
						scales={ganttScales}
						start={ganttStart}
						end={ganttEnd}
						cellWidth={40}
						cellHeight={32}
						readonly={true}
						columns={[{ id: 'text', header: 'Project', width: 240 }]}
						taskTemplate={GanttTaskBar}
					/>
				</WillowDark>
			</div>
		{/if}

		<!-- Legend -->
		<div class="mt-3 flex gap-5 text-xs text-muted-foreground">
			{#each projects as project, i}
				{@const dl = timeline.deadlines.find(
					(d) => d.title === project.title.split('\u2014')[0].trim(),
				)}
				<span class="flex items-center gap-1.5">
					<span class="inline-block h-2 w-2 rounded-sm" style:background={colorFor(i)}></span>
					{project.title.split('\u2014')[0].trim()}
					{#if dl}
						<span class="text-muted-foreground/70">— {formatDate(dl.date)}</span>
					{/if}
				</span>
			{/each}
		</div>
	</Card.Content>
</Card.Root>
