<script lang="ts">
import type { BookGraphProvenance, BookGraphSourceRef } from "@/types/book";
import {
	BOOK_GRAPH_BASIS_LABELS,
	BOOK_GRAPH_PROVENANCE_LABELS,
} from "@/types/book";

interface Props {
	provenance: BookGraphProvenance;
	sourceRefs?: BookGraphSourceRef[];
}

const { provenance, sourceRefs = [] }: Props = $props();
</script>

<div class="mt-3 text-xs">
	<span
		class="inline-flex rounded-full bg-(--btn-regular-bg) px-2.5 py-1 font-semibold text-neutral-600 dark:text-neutral-300"
	>
		{BOOK_GRAPH_PROVENANCE_LABELS[provenance]}
	</span>

	{#if sourceRefs.length > 0}
		<details class="mt-2">
			<summary class="cursor-pointer font-medium text-(--primary)">
				查看内容依据
			</summary>
			<ul class="mt-2 space-y-2 text-neutral-500 dark:text-neutral-400">
				{#each sourceRefs as source}
					<li class="rounded-lg bg-(--btn-regular-bg) px-3 py-2">
						<p>
							<strong class="text-neutral-700 dark:text-neutral-200">
								{BOOK_GRAPH_BASIS_LABELS[source.basis]}
							</strong>
							<span class="mx-1" aria-hidden="true">·</span>
							{source.locator}
						</p>
						{#if source.quote}
							<blockquote class="mt-2 border-l-2 border-(--primary) pl-3 leading-6">
								{source.quote}
							</blockquote>
						{/if}
					</li>
				{/each}
			</ul>
		</details>
	{/if}
</div>
