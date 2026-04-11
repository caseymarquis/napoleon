<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { getNextUp, colorFor } from './utils';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let { projects }: { projects: Project[] } = $props();
</script>

<Card.Root>
	<Card.Header>
		<Card.Title class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
			Next Up (per project)
		</Card.Title>
	</Card.Header>
	<Card.Content class="flex flex-col gap-2.5">
		{#each projects as project, i}
			{@const next = getNextUp(project)}
			<div
				class="rounded-md border bg-background p-3.5 transition-colors hover:bg-muted/50"
				style:border-left="3px solid {colorFor(i)}"
			>
				<div class="mb-1 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">
					{project.title}
				</div>
				{#if next}
					<div class="text-sm font-semibold leading-snug">{next.title}</div>
					{#if next.description}
						<div class="mt-1 text-xs leading-snug text-muted-foreground">{next.description}</div>
					{/if}
					<div class="mt-1.5">
						<Badge
							variant={next.risk === 'high' ? 'destructive' : 'secondary'}
						>
							{next.risk} risk
						</Badge>
					</div>
				{:else}
					<div class="text-sm font-semibold text-chart-2">All tasks complete</div>
				{/if}
			</div>
		{/each}
	</Card.Content>
</Card.Root>
