<script lang="ts">
import type { BookGraphNode, BookMapData, BookMapPart } from "@/types/book";
import {
	BOOK_GRAPH_NODE_KIND_LABELS,
	BOOK_MAP_ARCHETYPE_LABELS,
	BOOK_MAP_PART_ROLE_LABELS,
	BOOK_MAP_TRANSITION_RELATION_LABELS,
} from "@/types/book";
import BookGraphEvidence from "./BookGraphEvidence.svelte";

interface Props {
	bookMap: BookMapData;
	nodes: BookGraphNode[];
}

const { bookMap, nodes }: Props = $props();
const orderedParts = [...bookMap.parts].sort((a, b) => a.order - b.order);
const nodeById = new Map(nodes.map((node) => [node.id, node]));

function conceptsForPart(part: BookMapPart): BookGraphNode[] {
	return part.conceptNodeIds.flatMap((nodeId) => {
		const node = nodeById.get(nodeId);
		return node ? [node] : [];
	});
}
</script>

<section aria-labelledby="book-map-spine-heading">
	<div
		class="rounded-2xl border border-(--primary)/35 bg-linear-to-br from-(--primary)/12 via-(--card-bg) to-(--card-bg) p-5 md:p-6"
	>
		<div class="flex flex-wrap items-center gap-2">
			<span
				class="rounded-full bg-(--primary)/12 px-3 py-1 text-xs font-semibold text-(--primary)"
			>
				{BOOK_MAP_ARCHETYPE_LABELS[bookMap.archetype]}
			</span>
			<span class="text-xs text-neutral-400">作者论述顺序</span>
		</div>
		<p class="mt-5 text-xs font-semibold tracking-wide text-(--primary)">
			全书核心问题
		</p>
		<h3
			id="book-map-spine-heading"
			class="mt-1 max-w-4xl text-xl leading-8 font-bold text-neutral-900 md:text-2xl dark:text-neutral-100"
		>
			{bookMap.coreQuestion.text}
		</h3>
		<BookGraphEvidence
			provenance={bookMap.coreQuestion.provenance}
			sourceRefs={bookMap.coreQuestion.sourceRefs}
		/>

		<div
			class="mt-5 rounded-xl border border-(--line-divider) bg-(--card-bg)/80 p-4"
		>
			<p class="text-xs font-semibold text-neutral-400">全书主张</p>
			<p class="mt-1.5 leading-7 text-neutral-700 dark:text-neutral-200">
				{bookMap.thesis.text}
			</p>
			<BookGraphEvidence
				provenance={bookMap.thesis.provenance}
				sourceRefs={bookMap.thesis.sourceRefs}
			/>
		</div>
	</div>

	<ol class="book-map-spine mt-5 space-y-0">
		{#each orderedParts as part, index}
			<li class="book-map-step relative pb-5 pl-10 md:pl-14">
				<div
					class="absolute top-5 left-0 z-1 flex size-8 items-center justify-center rounded-full border-2 border-(--primary) bg-(--card-bg) text-sm font-bold text-(--primary) md:size-10"
					aria-hidden="true"
				>
					{part.order}
				</div>

				<article
					class="rounded-2xl border border-(--line-divider) bg-(--card-bg) p-4 shadow-sm md:p-5"
					aria-labelledby={`book-map-part-${part.id}`}
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<p class="text-xs font-semibold tracking-wide text-(--primary)">
								{BOOK_MAP_PART_ROLE_LABELS[part.role]}
							</p>
							<h4
								id={`book-map-part-${part.id}`}
								class="mt-1 text-lg font-bold text-neutral-900 dark:text-neutral-100"
							>
								{part.title}
							</h4>
						</div>
						<span
							class="rounded-full bg-(--btn-regular-bg) px-2.5 py-1 text-xs text-neutral-500 dark:text-neutral-400"
						>
							第 {part.order} 步
						</span>
					</div>

					<div class="mt-4 grid gap-3 lg:grid-cols-2">
						<div class="rounded-xl bg-(--btn-regular-bg) p-3.5">
							<p class="text-xs font-semibold text-neutral-400">本章追问</p>
							<p class="mt-1.5 text-sm leading-6 text-neutral-700 dark:text-neutral-200">
								{part.question}
							</p>
						</div>
						<div class="rounded-xl bg-(--primary)/8 p-3.5">
							<p class="text-xs font-semibold text-(--primary)">推进结果</p>
							<p class="mt-1.5 text-sm leading-6 text-neutral-700 dark:text-neutral-200">
								{part.thesis}
							</p>
						</div>
					</div>

					<div
						class="mt-3 grid gap-2 text-sm text-neutral-600 sm:grid-cols-[1fr_auto_1fr] sm:items-center dark:text-neutral-300"
					>
						<p class="rounded-lg border border-(--line-divider) px-3 py-2.5">
							<span class="block text-xs text-neutral-400">进入本章前</span>
							{part.inputUnderstanding}
						</p>
						<span class="hidden text-(--primary) sm:block" aria-hidden="true">→</span>
						<p class="rounded-lg border border-(--line-divider) px-3 py-2.5">
							<span class="block text-xs text-neutral-400">读完本章后</span>
							{part.outputUnderstanding}
						</p>
					</div>

					{#if conceptsForPart(part).length > 0}
						<details class="mt-4">
							<summary class="cursor-pointer text-sm font-semibold text-(--primary)">
								查看本章关联概念（{conceptsForPart(part).length}）
							</summary>
							<ul class="mt-3 grid gap-2 sm:grid-cols-2">
								{#each conceptsForPart(part) as node}
									<li class="rounded-lg bg-(--btn-regular-bg) px-3 py-2.5">
										<div class="flex flex-wrap items-center gap-2">
											<strong class="text-sm text-neutral-800 dark:text-neutral-100">
												{node.label}
											</strong>
											<span class="text-xs text-neutral-400">
												{BOOK_GRAPH_NODE_KIND_LABELS[node.kind]}
											</span>
										</div>
										<p class="mt-1 text-xs leading-5 text-neutral-500 dark:text-neutral-400">
											{node.summary}
										</p>
									</li>
								{/each}
							</ul>
						</details>
					{/if}

					<BookGraphEvidence
						provenance={part.provenance}
						sourceRefs={part.sourceRefs}
					/>
				</article>

				{#if index < orderedParts.length - 1}
					{#each bookMap.transitions.filter((transition) => transition.source === part.id) as transition}
						<div
							class="mt-3 rounded-xl border border-dashed border-(--primary)/35 bg-(--primary)/6 px-4 py-3"
						>
							<p class="text-xs font-semibold text-(--primary)">
								下一步如何被引出 · {BOOK_MAP_TRANSITION_RELATION_LABELS[transition.relation]}
							</p>
							<p class="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
								{transition.rationale}
							</p>
							<BookGraphEvidence
								provenance={transition.provenance}
								sourceRefs={transition.sourceRefs}
							/>
						</div>
					{/each}
				{/if}
			</li>
		{/each}
	</ol>

	<div class="rounded-2xl border-2 border-(--primary)/40 bg-(--primary)/10 p-5 md:p-6">
		<p class="text-xs font-semibold tracking-wide text-(--primary)">全书落点</p>
		<p class="mt-2 text-lg leading-8 font-semibold text-neutral-800 dark:text-neutral-100">
			{bookMap.conclusion.text}
		</p>
		<BookGraphEvidence
			provenance={bookMap.conclusion.provenance}
			sourceRefs={bookMap.conclusion.sourceRefs}
		/>
	</div>
</section>

<style>
	.book-map-step::before {
		position: absolute;
		top: 2.5rem;
		bottom: -0.25rem;
		left: 0.95rem;
		width: 2px;
		background: color-mix(in srgb, var(--primary) 35%, transparent);
		content: "";
	}

	.book-map-step:last-child::before {
		display: none;
	}

	@media (min-width: 768px) {
		.book-map-step::before {
			left: 1.2rem;
		}
	}
</style>
