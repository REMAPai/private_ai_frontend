<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let onConfirm: () => void = () => {};

	const handleConfirm = () => {
		show = false;
		onConfirm();
	};
</script>

{#if show}
	<Modal bind:show size="sm">
		<div class="px-5 py-4">
			<div class="flex justify-between items-center mb-4">
				<div class="text-lg font-semibold dark:text-gray-100">
					{$i18n.t('Data Retention Notice')}
				</div>
			</div>

			<div class="text-sm text-gray-700 dark:text-gray-300 mb-6">
				{$i18n.t('By choosing this model, your data will be retained for 30 days, then gets deleted automatically.')}
			</div>

			<div class="flex justify-end">
				<button
					class="px-5 py-2.5 bg-gray-900 hover:bg-gray-850 text-gray-100 dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800 font-semibold rounded-lg transition-colors shadow-sm"
					on:click={handleConfirm}
					type="button"
				>
					{$i18n.t('I agree')}
				</button>
			</div>
		</div>
	</Modal>
{/if}
