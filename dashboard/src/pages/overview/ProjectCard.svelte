<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { buildTaskMap, resolveTaskStatus, daysUntil, formatDate, deadlineClass } from './utils';
	import * as Card from '$lib/components/ui/card';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import * as Table from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';

	let { project, forceOpen = false }: { project: Project; forceOpen?: boolean } = $props();

	let open = $state(false);
	$effect(() => {
		if (forceOpen) open = true;
	});
	let taskMap = $derived(buildTaskMap(project));
	let days = $derived(project.deadline ? daysUntil(project.deadline) : null);
	let statusCounts = $derived.by(() => {
		const counts = { not_started: 0, in_progress: 0, completed: 0, blocked: 0 };
		project.tasks.forEach((t) => {
			counts[resolveTaskStatus(t, taskMap)]++;
		});
		return counts;
	});

	const statusLabel: Record<string, string> = {
		not_started: 'Not Started',
		in_progress: 'In Progress',
		completed: 'Completed',
		blocked: 'Blocked',
	};

	function statusVariant(s: string): 'default' | 'secondary' | 'destructive' | 'outline' {
		if (s === 'completed') return 'default';
		if (s === 'in_progress') return 'secondary';
		if (s === 'blocked') return 'destructive';
		return 'outline';
	}

	function riskVariant(r: string): 'default' | 'secondary' | 'destructive' | 'outline' {
		if (r === 'high') return 'destructive';
		if (r === 'medium') return 'secondary';
		return 'outline';
	}
</script>

<Collapsible.Root bind:open class="mb-4">
	<Card.Root>
		<Collapsible.Trigger class="w-full cursor-pointer">
			<Card.Header class="flex flex-row items-center justify-between">
				<div class="flex items-center gap-3">
					<span
						class="text-xs text-muted-foreground transition-transform"
						class:rotate-90={open}
					>
						&#9654;
					</span>
					<Card.Title>{project.title}</Card.Title>
					<span class="text-sm text-muted-foreground">
						{statusCounts.completed}/{project.tasks.length} done
					</span>
					{#if project.committedTo}
						<span class="text-sm text-muted-foreground">{project.committedTo}</span>
					{/if}
				</div>
				{#if days != null}
					<Badge variant={days <= 3 ? 'destructive' : days <= 10 ? 'secondary' : 'outline'}>
						{formatDate(project.deadline)} ({days}d)
					</Badge>
				{/if}
			</Card.Header>
		</Collapsible.Trigger>

		<Collapsible.Content>
			<Card.Content>
				<!-- Info panels -->
				{#if project.unknowns.length || project.constraints.length || project.externalDeps.length}
					<div class="mb-6 grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4">
						{#if project.unknowns.length}
							<div class="rounded-md border bg-background p-4">
								<h4 class="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
									Unknowns
								</h4>
								<ul class="space-y-1 text-sm">
									{#each project.unknowns as u}
										<li class="text-muted-foreground">• {u}</li>
									{/each}
								</ul>
							</div>
						{/if}
						{#if project.constraints.length}
							<div class="rounded-md border bg-background p-4">
								<h4 class="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
									Constraints
								</h4>
								<ul class="space-y-1 text-sm">
									{#each project.constraints as c}
										<li class="text-muted-foreground">• {c}</li>
									{/each}
								</ul>
							</div>
						{/if}
						{#if project.externalDeps.length}
							<div class="rounded-md border bg-background p-4">
								<h4 class="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
									External Dependencies
								</h4>
								<ul class="space-y-1 text-sm">
									{#each project.externalDeps as dep}
										<li class={dep.resolved ? 'text-chart-2' : 'text-chart-4'}>
											{dep.resolved ? '✓' : '○'} {dep.description}
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Tasks table -->
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Task</Table.Head>
							<Table.Head>Status</Table.Head>
							<Table.Head>Risk</Table.Head>
							<Table.Head>Blocked By</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each project.tasks as task}
							{@const resolved = resolveTaskStatus(task, taskMap)}
							<Table.Row>
								<Table.Cell class="font-medium">
									{task.title}
									{#if task.description}
										<div class="mt-0.5 text-xs text-muted-foreground">{task.description}</div>
									{/if}
								</Table.Cell>
								<Table.Cell>
									<Badge variant={statusVariant(resolved)}>{statusLabel[resolved]}</Badge>
								</Table.Cell>
								<Table.Cell>
									<Badge variant={riskVariant(task.risk)}>{task.risk}</Badge>
								</Table.Cell>
								<Table.Cell>
									{#if task.blockedBy.length}
										{#each task.blockedBy as blockerId}
											{@const dep = taskMap[blockerId]}
											<Badge variant="destructive" class="mr-1">
												{dep ? dep.title.split('(')[0].trim() : blockerId}
											</Badge>
										{/each}
									{:else}
										<span class="text-muted-foreground">—</span>
									{/if}
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>

				{#if project.minimumDelivery}
					<div class="mt-5 rounded-r-md border-l-[3px] border-destructive-foreground bg-destructive/10 p-3 text-sm text-muted-foreground">
						<strong class="text-destructive-foreground">Minimum delivery:</strong>
						{project.minimumDelivery}
					</div>
				{/if}
			</Card.Content>
		</Collapsible.Content>
	</Card.Root>
</Collapsible.Root>
