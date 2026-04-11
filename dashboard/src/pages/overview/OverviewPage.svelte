<script lang="ts">
	import type { OverviewPageContract } from './OverviewPageContract';
	import CapacityTimeline from './CapacityTimeline.svelte';
	import NextUpPanel from './NextUpPanel.svelte';
	import ReadinessPanel from './ReadinessPanel.svelte';
	import ProjectCard from './ProjectCard.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import { Spinner } from '$lib/components/ui/spinner';

	let { contract }: { contract: OverviewPageContract } = $props();

	let expandedProject = $state<string | null>(null);

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
	<div class="mb-8 grid grid-cols-2 gap-5">
		<div class="col-span-2">
			<CapacityTimeline
				projects={contract.projects}
				onSelectProject={selectProject}
				onUpdateTask={(projectId, taskId, updates) => contract.updateTask(projectId, taskId, updates)}
			/>
		</div>
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
