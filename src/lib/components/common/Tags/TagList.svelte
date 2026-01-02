<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import TagItem from './TagItem.svelte';
	const dispatch = createEventDispatcher();

	export let tags = [];
</script>

{#each tags as tag}
	<TagItem
		{tag}
		onDelete={() => {
			dispatch('delete', tag.name);
		}}
	/>
{/each}
