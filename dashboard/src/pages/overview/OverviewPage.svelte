<script lang="ts">
	import type { OverviewPageContract } from './OverviewPageContract';
	import CapacityTimeline, { type TaskKey } from './CapacityTimeline.svelte';
	import GanttDetailPanel from './GanttDetailPanel.svelte';
	import NextUpPanel from './NextUpPanel.svelte';
	import ReadinessPanel from './ReadinessPanel.svelte';
	import ProjectCard from './ProjectCard.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import { Spinner } from '$lib/components/ui/spinner';

	let { contract }: { contract: OverviewPageContract } = $props();

	let selectedTaskKey = $state<TaskKey>(null);
	let expandedProject = $state<string | null>(null);

	// Resolve selected task's metadata from the live project data
	let selectedTaskInfo = $derived.by(() => {
		if (!selectedTaskKey) return null;
		const project = contract.projects.find((p) => p.id === selectedTaskKey!.projectId);
		if (!project) return null;
		const task = project.tasks.find((t) => t.id === selectedTaskKey!.taskId);
		if (!task) {
			// Fall back to a summary-like view if the task is gone but project exists
			return {
				task: { type: 'summary', text: project.title, _projectId: project.id },
				project,
			};
		}
		return {
			task: {
				type: 'task',
				text: task.title,
				_projectId: project.id,
				_taskId: task.id,
				_risk: task.risk,
				_est50: task.est50,
				_est90: task.est90,
				_description: task.description,
				_atomic: task.atomic,
				_status: task.status,
			},
			project,
		};
	});

	function selectProject(projectId: string) {
		expandedProject = projectId;
		const el = document.getElementById(`project-${projectId}`);
		el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
</script>

{#if contract.loading}
	<div class="flex items-center justify-center py-16">
		<Spinner class="text-muted-foreground" />
	</div>
{:else if contract.projects.length === 0}
	<div class="py-16 text-center text-muted-foreground">No projects found.</div>
{:else}
	<!-- Gantt + detail panel side by side -->
	<div class="mb-8 grid gap-5" class:grid-cols-[2fr_1fr]={selectedTaskInfo} class:grid-cols-1={!selectedTaskInfo}>
		<CapacityTimeline projects={contract.projects} bind:selectedTaskKey />
		{#if selectedTaskInfo}
			<GanttDetailPanel
				task={selectedTaskInfo.task}
				project={selectedTaskInfo.project}
				onUpdateTask={(projectId, taskId, updates) => contract.updateTask(projectId, taskId, updates)}
				onClose={() => (selectedTaskKey = null)}
			/>
		{/if}
	</div>

	<!-- NextUp + Readiness -->
	<div class="mb-8 grid grid-cols-2 gap-5">
		<NextUpPanel projects={contract.projects} />
		<ReadinessPanel projects={contract.projects} />
	</div>

	<div class="mb-4 flex items-center gap-3">
		<span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
			Project Details
		</span>
		<Separator class="flex-1" />
	</div>

	{#each contract.projects as project}
		<div id="project-{project.id}">
			<ProjectCard {project} forceOpen={expandedProject === project.id} />
		</div>
	{/each}
{/if}
