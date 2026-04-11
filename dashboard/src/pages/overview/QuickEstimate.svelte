<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let {
		label,
		value,
		onchange,
	}: {
		label: string;
		value: number | null;
		onchange: (v: number | null) => void;
	} = $props();

	const presets = [
		{ label: '⅕', value: 0.2 },
		{ label: '¼', value: 0.25 },
		{ label: '½', value: 0.5 },
		{ label: '¾', value: 0.75 },
		{ label: '1', value: 1 },
		{ label: '2', value: 2 },
	];

	let isPreset = $derived(value != null && presets.some((p) => p.value === value));

	function submitCustom(raw: string) {
		const num = parseFloat(raw);
		onchange(isNaN(num) || raw === '' ? null : num);
	}
</script>

<div class="flex items-center gap-1.5">
	<span class="w-12 text-xs text-muted-foreground">{label}</span>
	{#each presets as p}
		<Button
			variant={value === p.value ? 'default' : 'ghost'}
			size="sm"
			class="h-6 min-w-6 px-1.5 text-xs"
			onclick={() => onchange(p.value)}
		>
			{p.label}
		</Button>
	{/each}
	<Input
		type="number"
		step="0.25"
		placeholder="…"
		class="hide-spinners h-6 w-14 text-xs {!isPreset && value != null ? 'border-primary' : ''}"
		value={!isPreset ? (value ?? '') : ''}
		onchange={(e) => submitCustom(e.currentTarget.value)}
	/>
</div>
