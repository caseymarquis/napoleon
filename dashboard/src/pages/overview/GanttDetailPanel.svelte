<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { formatDate } from './utils';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as Select from '$lib/components/ui/select';
	import QuickEstimate from './QuickEstimate.svelte';

	let {
		task,
		project,
		onUpdateTask,
	}: {
		task: any;
		project: Project | undefined;
		onUpdateTask?: (projectId: string, taskId: string, updates: Record<string, any>) => void;
	} = $props();

	let done = $derived(project ? project.tasks.filter((t) => t.status === 'completed').length : 0);
	let total = $derived(project ? project.tasks.length : 0);

	function update(field: string, value: any) {
		if (task._projectId && task._taskId && onUpdateTask) {
			onUpdateTask(task._projectId, task._taskId, { [field]: value });
		}
	}

	function updateNumber(field: string, raw: string) {
		const num = parseFloat(raw);
		update(field, isNaN(num) ? null : num);
	}
</script>

<div class="mt-3 rounded-md border border-border bg-card p-4">
	{#if task.type === 'summary' && project}
		<div class="mb-1 text-sm font-semibold">{project.title}</div>
		{#if project.description}
			<div class="mb-2 text-xs text-muted-foreground">{project.description}</div>
		{/if}
		<div class="flex flex-wrap gap-2 text-xs">
			<Badge variant="outline">{done}/{total} done</Badge>
			{#if project.deadline}
				<Badge variant="outline">{formatDate(project.deadline)}</Badge>
			{/if}
			{#if project.unknowns.length}
				<Badge variant="secondary">{project.unknowns.length} unknowns</Badge>
			{/if}
			{#if project.constraints.length}
				<Badge variant="secondary">{project.constraints.length} constraints</Badge>
			{/if}
		</div>
	{:else}
		<div class="mb-3 text-sm font-semibold">{task.text}</div>
		{#if task._description}
			<div class="mb-3 text-xs text-muted-foreground">{task._description}</div>
		{/if}

		{#if project}
			<div class="mb-3 text-xs text-muted-foreground">
				<Badge variant="outline">{project.title}</Badge>
			</div>
		{/if}

		<!-- Editable fields -->
		<div class="flex flex-col gap-2">
			<QuickEstimate label="Est 50%" value={task._est50} onchange={(v) => update('est50', v)} />
			<QuickEstimate label="Est 90%" value={task._est90} onchange={(v) => update('est90', v)} />

			<div class="flex items-center gap-4">
				<label class="flex items-center gap-1.5">
					<span class="text-xs text-muted-foreground">Risk</span>
					<Select.Root
						type="single"
						value={task._risk || 'low'}
						onValueChange={(v) => update('risk', v)}
					>
						<Select.Trigger class="h-7 w-24 text-xs">
							{task._risk || 'low'}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="low">low</Select.Item>
							<Select.Item value="medium">medium</Select.Item>
							<Select.Item value="high">high</Select.Item>
						</Select.Content>
					</Select.Root>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-xs text-muted-foreground">Atomic</span>
					<Checkbox
						checked={task._atomic || false}
						onCheckedChange={(v) => update('atomic', v)}
					/>
				</label>
			</div>
		</div>
	{/if}
</div>
