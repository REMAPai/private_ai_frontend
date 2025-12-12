<script lang="ts">
	export let className = '';
	export let strokeWidth: number | string = 1;
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	class={className}
>
	<!-- antennae -->
	<path d="M9 4 7.5 2.5" />
	<path d="M15 4 16.5 2.5" />

	<!-- head / top -->
	<path d="M10 7V6a2 2 0 0 1 4 0v1" />

	<!-- body -->
	<rect x="7" y="7" width="10" height="13" rx="5" />

	<!-- center line -->
	<path d="M12 11v9" />

	<!-- legs -->
	<path d="M7 11H4" />
	<path d="M7 15H4" />
	<path d="M17 11h3" />
	<path d="M17 15h3" />
</svg>
