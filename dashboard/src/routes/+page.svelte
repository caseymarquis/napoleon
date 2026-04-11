<script lang="ts">
	import OverviewPage from '../pages/overview/OverviewPage.svelte';
	import type { OverviewPageContract, Project } from '../pages/overview/OverviewPageContract';
	import * as Select from '$lib/components/ui/select';

	const today = new Date();
	const dateStr = today.toLocaleDateString('en-US', {
		weekday: 'long',
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});

	let contract: OverviewPageContract = $state({
		projects: [],
		repos: [],
		activeRepo: '',
		loading: true,

		async selectRepo(hash: string) {
			contract.activeRepo = hash;
			location.hash = hash;
			await contract.refresh();
		},

		async refresh() {
			contract.loading = true;
			try {
				const res = await fetch(`/api/projects?p=${contract.activeRepo}`);
				const projects: Project[] = await res.json();
				projects.sort(
					(a, b) =>
						(a.priority || 99) - (b.priority || 99) ||
						new Date(a.deadline).getTime() - new Date(b.deadline).getTime(),
				);
				contract.projects = projects;
			} catch {
				contract.projects = [];
			}
			contract.loading = false;
		},

		async updateTask(projectId: string, taskId: string, updates: Partial<Project['tasks'][number]>) {
			await fetch('/api/task/update', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					phash: contract.activeRepo,
					project: projectId,
					task: taskId,
					updates,
				}),
			});
			// Data will refresh via polling, but update locally for instant feedback
			for (const p of contract.projects) {
				if (p.id === projectId) {
					const task = p.tasks.find((t) => t.id === taskId);
					if (task) Object.assign(task, updates);
				}
			}
		},
	});

	async function init() {
		try {
			const res = await fetch('/api/repos');
			contract.repos = await res.json();
		} catch {
			contract.repos = [];
		}

		const hashRepo = location.hash.slice(1);
		if (hashRepo) {
			contract.activeRepo = hashRepo;
		} else if (contract.repos.length > 0) {
			contract.activeRepo = contract.repos[0].hash;
			location.hash = contract.activeRepo;
		}

		if (contract.activeRepo) {
			await contract.refresh();
		} else {
			contract.loading = false;
		}

		// Poll for data changes only (not UI — Vite HMR handles that)
		let knownHash: string | null = null;
		setInterval(async () => {
			if (!contract.activeRepo) return;
			try {
				const res = await fetch(`/api/hash?p=${contract.activeRepo}`);
				const { hash } = await res.json();
				if (knownHash === null) {
					knownHash = hash;
				} else if (hash !== knownHash) {
					knownHash = hash;
					// Soft refresh — don't flash loading spinner
					const res2 = await fetch(`/api/projects?p=${contract.activeRepo}`);
					const projects: Project[] = await res2.json();
					projects.sort(
						(a, b) =>
							(a.priority || 99) - (b.priority || 99) ||
							new Date(a.deadline).getTime() - new Date(b.deadline).getTime(),
					);
					contract.projects = projects;
				}
			} catch {}
		}, 2000);
	}

	init();
</script>

<div class="mx-auto max-w-[1400px] px-10 py-8">
	<div class="mb-8 flex items-end justify-between border-b border-border pb-4">
		<div>
			<h1 class="text-2xl font-bold tracking-tight">Project Dashboard</h1>
			<div class="text-sm text-muted-foreground">{dateStr}</div>
		</div>
		{#if contract.repos.length > 0}
			<Select.Root
				type="single"
				value={contract.activeRepo}
				onValueChange={(v) => { if (v) contract.selectRepo(v); }}
			>
				<Select.Trigger class="w-48">
					{contract.repos.find((r) => r.hash === contract.activeRepo)?.name || contract.activeRepo}
				</Select.Trigger>
				<Select.Content>
					{#each contract.repos as repo}
						<Select.Item value={repo.hash}>{repo.name || repo.hash}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{/if}
	</div>

	<OverviewPage {contract} />
</div>
