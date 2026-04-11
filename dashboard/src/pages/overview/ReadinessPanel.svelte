<script lang="ts">
	import type { Project } from './OverviewPageContract';
	import { assessReadiness, daysUntil } from './utils';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let { projects }: { projects: Project[] } = $props();

	function gradeVariant(gradeClass: string): 'default' | 'secondary' | 'destructive' {
		if (gradeClass === 'grade-well-defined') return 'default';
		if (gradeClass === 'grade-partial') return 'secondary';
		return 'destructive';
	}

	function factorVariant(cls: string): 'default' | 'secondary' | 'destructive' | 'outline' {
		if (cls === 'ok') return 'default';
		if (cls === 'warn') return 'secondary';
		if (cls === 'bad') return 'destructive';
		return 'outline';
	}
</script>

<Card.Root>
	<Card.Header>
		<Card.Title class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
			Project Readiness
		</Card.Title>
	</Card.Header>
	<Card.Content class="flex flex-col gap-2.5">
		{#each projects as project}
			{@const r = assessReadiness(project)}
			{@const days = daysUntil(project.deadline)}
			<div class="rounded-md border bg-background p-3.5 transition-colors hover:bg-muted/50">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm font-semibold">{project.title.split('\u2014')[0].trim()}</span>
					<Badge variant={gradeVariant(r.gradeClass)}>{r.grade}</Badge>
				</div>
				<div class="flex flex-wrap gap-1.5">
					{#each r.factors as f}
						<Badge variant={factorVariant(f.cls)}>{f.label}</Badge>
					{/each}
					<Badge variant={days <= 3 ? 'destructive' : days <= 10 ? 'secondary' : 'default'}>
						{days}d left
					</Badge>
				</div>
			</div>
		{/each}
	</Card.Content>
</Card.Root>
