<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { computeSequentialTimeline, colorFor, formatDate, DEFAULT_EST } from './utils';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Gantt, WillowDark } from '@svar-ui/svelte-gantt';
	import GanttTaskBar from './GanttTaskBar.svelte';
	import GanttDetailPanel from './GanttDetailPanel.svelte';

	let {
		projects,
		onSelectProject,
		onUpdateTask,
	}: {
		projects: Project[];
		onSelectProject?: (projectId: string) => void;
		onUpdateTask?: (projectId: string, taskId: string, updates: Record<string, any>) => void;
	} = $props();

	let timeline = $derived(computeSequentialTimeline(projects));
	let deadlineDays = $derived(timeline.deadlines.map((d) => d.day));
	let latestDeadline = $derived(deadlineDays.length > 0 ? Math.max(...deadlineDays) : 0);
	let overBy = $derived(
		latestDeadline > 0 ? Math.round((timeline.totalWork - latestDeadline) * 10) / 10 : 0,
	);
	let capacityStatus = $derived(overBy > 5 ? 'over' : overBy > 0 ? 'tight' : 'ok');

	const statusStyle = {
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
				});

				dayOffset += dur;
			}

			// Project summary (parent)
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

	let selectedTaskKey = $state<{ projectId: string; taskId: string } | null>(null);

	// Re-derive selectedTask from ganttTasks whenever data refreshes
	let selectedTask = $derived.by(() => {
		if (!selectedTaskKey) return null;
		return ganttTasks.find(
			(t) => t._projectId === selectedTaskKey!.projectId && t._taskId === selectedTaskKey!.taskId,
		) ?? ganttTasks.find(
			(t) => t._projectId === selectedTaskKey!.projectId && t.type === 'summary',
		) ?? null;
	});

	function ganttInit(api: any) {
		api.on('select-task', (ev: any) => {
			const task = ganttTasks.find((t) => t.id === ev.id);
			if (!task || task.text === '') return;
			selectedTaskKey = { projectId: task._projectId, taskId: task._taskId };
		});
	}

	function closeDetail() {
		selectedTaskKey = null;
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
				<span class="text-2xl font-bold leading-tight {statusStyle[capacityStatus]}">
					{timeline.totalWork}d
				</span>
				<span class="mt-0.5 text-xs text-muted-foreground">total work (est.)</span>
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

		<!-- Detail panel -->
		{#if selectedTask}
			<GanttDetailPanel
				task={selectedTask}
				project={projects.find((p) => p.id === selectedTask._projectId)}
				{onUpdateTask}
				onClose={closeDetail}
			/>
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
