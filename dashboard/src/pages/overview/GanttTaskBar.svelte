<script>
	let { data } = $props();

	let statusIcon = $derived.by(() => {
		if (data.type === 'summary') return '';
		if (data._status === 'in_progress') return '▶';
		if (data._status === 'completed') return '✓';
		return '';
	});

	let warnings = $derived.by(() => {
		if (data.type === 'summary') return [];
		const w = [];
		if (!data._atomic) w.push('🧩');
		if (data._risk === 'high') w.push('🔥');
		if (data._est50 == null) w.push('🎲');
		return w;
	});

	let tooltip = $derived.by(() => {
		if (data.type === 'summary') return data.text;
		const parts = [data.text];
		if (data._status) parts.push(`Status: ${data._status.replace('_', ' ')}`);
		if (data._description) parts.push(data._description);
		if (data._est50 != null) parts.push(`Est: ${data._est50}d / ${data._est90 ?? '?'}d`);
		if (data._risk) parts.push(`Risk: ${data._risk}`);
		if (!data._atomic) parts.push('⚠ Not atomic — needs breakdown');
		if (data._est50 == null) parts.push('⚠ No estimate');
		return parts.join('\n');
	});
</script>

<div class="bar-wrapper" title={tooltip}>
	{#if data._isBuffer}
		<div class="task-label buffer-label">🛡️ {data.text || ''}</div>
	{:else if data.type !== 'summary'}
		<div class="task-label">
			{#if statusIcon}<span class="status-icon">{statusIcon}</span>{/if}
			{#if warnings.length}<span class="warnings">{warnings.join('')}</span>{/if}
			{data.text || ''}
		</div>
	{/if}
</div>

<style>
	.bar-wrapper {
		width: 100%;
		height: 100%;
		cursor: pointer;
	}
	.task-label {
		position: absolute;
		left: 100%;
		top: -2px;
		padding: 0 6px;
		font-size: 11px;
		white-space: nowrap;
		color: var(--wx-gantt-bar-color, #ccc);
	}
	.status-icon {
		margin-right: 3px;
		font-size: 10px;
		color: #58a6ff;
	}
	.warnings {
		margin-right: 4px;
		font-size: 16px;
		vertical-align: middle;
	}
	.buffer-label {
		opacity: 0.6;
		font-style: italic;
	}
</style>
