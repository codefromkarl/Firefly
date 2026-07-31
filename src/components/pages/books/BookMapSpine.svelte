<script lang="ts">
import type {
	BookArgumentCard,
	BookGraphNode,
	BookMapData,
	BookMapPart,
} from "@/types/book";
import {
	BOOK_ARGUMENT_CARD_KIND_LABELS,
	BOOK_ARGUMENT_CONTEXT_LABELS,
	BOOK_GRAPH_NODE_KIND_LABELS,
	BOOK_MAP_ARCHETYPE_LABELS,
	BOOK_MAP_PART_MATURITY_LABELS,
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

function conceptsForCard(card: BookArgumentCard): BookGraphNode[] {
	return card.conceptNodeIds.flatMap((nodeId) => {
		const node = nodeById.get(nodeId);
		return node ? [node] : [];
	});
}
</script>

<section class="min-w-0" aria-labelledby="book-map-spine-heading">
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
			30 秒整书主线 · 核心问题
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
			<p class="text-xs font-semibold text-neutral-400">全书回答</p>
			<p class="mt-1.5 leading-7 text-neutral-700 dark:text-neutral-200">
				{bookMap.thesis.text}
			</p>
			<BookGraphEvidence
				provenance={bookMap.thesis.provenance}
				sourceRefs={bookMap.thesis.sourceRefs}
			/>
		</div>
	</div>

	<div
		class="book-map-scroll mt-5 max-w-full overflow-x-auto pb-2"
		tabindex="0"
		role="region"
		aria-label="全书各部分论证长卷"
	>
		<ol
			class="book-map-spine"
			style={`--book-map-part-count: ${orderedParts.length}`}
		>
			{#each orderedParts as part, index}
				<li class="book-map-step relative pb-5 pl-10 md:pl-14">
					<div
						class="book-map-step-number absolute top-5 left-0 z-1 flex size-8 items-center justify-center rounded-full border-2 border-(--primary) bg-(--card-bg) text-sm font-bold text-(--primary) md:size-10"
						aria-hidden="true"
					>
						{part.order}
					</div>

					<article
						class="book-map-part rounded-2xl border border-(--line-divider) bg-(--card-bg) p-4 shadow-sm md:p-5"
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
								class:maturity-outline={part.maturity === "outline"}
								class="maturity-badge rounded-full bg-(--btn-regular-bg) px-2.5 py-1 text-xs font-semibold text-neutral-500 dark:text-neutral-400"
							>
								{BOOK_MAP_PART_MATURITY_LABELS[part.maturity]}
							</span>
						</div>

						<div class="mt-4 grid gap-3">
							<div class="rounded-xl bg-(--btn-regular-bg) p-3.5">
								<p class="text-xs font-semibold text-neutral-400">问 · 本部分追问</p>
								<p
									class="mt-1.5 text-sm leading-6 text-neutral-700 dark:text-neutral-200"
								>
									{part.question}
								</p>
							</div>
							<div class="rounded-xl bg-(--primary)/8 p-3.5">
								<p class="text-xs font-semibold text-(--primary)">答 · 阶段性回答</p>
								<p
									class="mt-1.5 text-sm leading-6 text-neutral-700 dark:text-neutral-200"
								>
									{part.thesis}
								</p>
							</div>
						</div>

						<div
							class="mt-3 grid gap-2 text-sm text-neutral-600 dark:text-neutral-300"
						>
							<p class="rounded-lg border border-(--line-divider) px-3 py-2.5">
								<span class="block text-xs text-neutral-400">进入本部分前</span>
								{part.inputUnderstanding}
							</p>
							<p class="rounded-lg border border-(--line-divider) px-3 py-2.5">
								<span class="block text-xs text-neutral-400">离开本部分后</span>
								{part.outputUnderstanding}
							</p>
						</div>

						{#if part.maturity === "outline"}
							<div
								class="mt-4 rounded-xl border border-dashed border-amber-500/45 bg-amber-500/8 p-4"
							>
								<p class="text-sm font-semibold text-amber-700 dark:text-amber-300">
									本部分只有总纲，细粒度论证待补充
								</p>
								<p class="mt-1 text-xs leading-5 text-neutral-500 dark:text-neutral-400">
									获得可核验的原书内容或个人笔记后，再补充机制、证据、实践与边界。
								</p>
							</div>
						{:else if part.argumentCards.length > 0}
							<div class="mt-4 space-y-3" aria-label={`${part.title}论证卡`}>
								{#each part.argumentCards as card}
									<article
										class="argument-card rounded-xl border border-(--line-divider) bg-(--btn-regular-bg)/55 p-3.5"
										data-argument-kind={card.kind}
									>
										<div class="flex flex-wrap items-center gap-2">
											<span
												class="argument-kind rounded-full px-2.5 py-1 text-xs font-semibold"
											>
												{BOOK_ARGUMENT_CARD_KIND_LABELS[card.kind]}
											</span>
											<span
												class="rounded-full border border-(--line-divider) bg-(--card-bg) px-2.5 py-1 text-xs text-neutral-500 dark:text-neutral-400"
											>
												{BOOK_ARGUMENT_CONTEXT_LABELS[card.context]}
											</span>
										</div>
										<h5
											class="mt-3 text-sm font-bold text-neutral-800 dark:text-neutral-100"
										>
											{card.title}
										</h5>
										<p class="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
											{card.summary}
										</p>

										{#if conceptsForCard(card).length > 0}
											<ul class="mt-3 flex flex-wrap gap-1.5" aria-label="关联概念">
												{#each conceptsForCard(card) as node}
													<li
														class="rounded-md bg-(--card-bg) px-2 py-1 text-xs text-neutral-500 dark:text-neutral-400"
													>
														{node.label}
													</li>
												{/each}
											</ul>
										{/if}

										<BookGraphEvidence
											provenance={card.provenance}
											sourceRefs={card.sourceRefs}
										/>
									</article>
								{/each}
							</div>
						{/if}

						{#if conceptsForPart(part).length > 0}
							<details class="mt-4">
								<summary class="cursor-pointer text-sm font-semibold text-(--primary)">
									查看本部分关联概念（{conceptsForPart(part).length}）
								</summary>
								<ul class="mt-3 grid gap-2">
									{#each conceptsForPart(part) as node}
										<li class="rounded-lg bg-(--btn-regular-bg) px-3 py-2.5">
											<div class="flex flex-wrap items-center gap-2">
												<strong
													class="text-sm text-neutral-800 dark:text-neutral-100"
												>
													{node.label}
												</strong>
												<span class="text-xs text-neutral-400">
													{BOOK_GRAPH_NODE_KIND_LABELS[node.kind]}
												</span>
											</div>
											<p
												class="mt-1 text-xs leading-5 text-neutral-500 dark:text-neutral-400"
											>
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
								class="book-map-transition mt-3 rounded-xl border border-dashed border-(--primary)/35 bg-(--primary)/6 px-4 py-3"
							>
								<p class="text-xs font-semibold text-(--primary)">
									接 · {BOOK_MAP_TRANSITION_RELATION_LABELS[transition.relation]}
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
	</div>

	<div class="rounded-2xl border-2 border-(--primary)/40 bg-(--primary)/10 p-5 md:p-6">
		<p class="text-xs font-semibold tracking-wide text-(--primary)">全书阶段性落点</p>
		<p
			class="mt-2 text-lg leading-8 font-semibold text-neutral-800 dark:text-neutral-100"
		>
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

	.maturity-outline {
		background: color-mix(in srgb, #f59e0b 14%, transparent);
		color: #92400e;
	}

	.argument-kind {
		background: color-mix(in srgb, var(--primary) 12%, transparent);
		color: var(--primary);
	}

	.argument-card[data-argument-kind="evidence"] .argument-kind {
		background: color-mix(in srgb, #2563eb 13%, transparent);
		color: #1d4ed8;
	}

	.argument-card[data-argument-kind="manifestation"] .argument-kind,
	.argument-card[data-argument-kind="boundary"] .argument-kind {
		background: color-mix(in srgb, #e11d48 11%, transparent);
		color: #be123c;
	}

	.argument-card[data-argument-kind="practice"] .argument-kind {
		background: color-mix(in srgb, #16a34a 12%, transparent);
		color: #15803d;
	}

	:global(.dark) .maturity-outline {
		color: #fcd34d;
	}

	:global(.dark) .argument-card[data-argument-kind="evidence"] .argument-kind {
		color: #93c5fd;
	}

	:global(.dark)
		.argument-card:is(
			[data-argument-kind="manifestation"],
			[data-argument-kind="boundary"]
		)
		.argument-kind {
		color: #fda4af;
	}

	:global(.dark) .argument-card[data-argument-kind="practice"] .argument-kind {
		color: #86efac;
	}

	.book-map-scroll:focus-visible {
		border-radius: 1rem;
		outline: 2px solid var(--primary);
		outline-offset: 3px;
	}

	@media (min-width: 768px) {
		.book-map-step::before {
			left: 1.2rem;
		}
	}

	@media (min-width: 1024px) {
		.book-map-spine {
			display: grid;
			grid-template-columns: repeat(
				var(--book-map-part-count),
				minmax(18rem, 1fr)
			);
			gap: 1rem;
			min-width: max-content;
		}

		.book-map-step {
			display: flex;
			width: 20rem;
			flex-direction: column;
			padding: 3rem 0 1rem;
		}

		.book-map-step::before {
			top: 1.2rem;
			right: -1rem;
			bottom: auto;
			left: 50%;
			width: calc(50% + 1rem);
			height: 2px;
		}

		.book-map-step:not(:first-child)::after {
			position: absolute;
			top: 1.2rem;
			right: 50%;
			left: -1rem;
			height: 2px;
			background: color-mix(in srgb, var(--primary) 35%, transparent);
			content: "";
		}

		.book-map-step:last-child::before {
			display: none;
		}

		.book-map-step-number {
			top: 0;
			left: 50%;
			transform: translateX(-50%);
		}

		.book-map-part {
			flex: 1;
		}

		.book-map-transition {
			position: relative;
		}

		.book-map-transition::after {
			position: absolute;
			top: 50%;
			right: -0.75rem;
			border-top: 0.3rem solid transparent;
			border-bottom: 0.3rem solid transparent;
			border-left: 0.4rem solid var(--primary);
			content: "";
			transform: translateY(-50%);
		}
	}

	@media (min-width: 1280px) {
		.book-map-step {
			width: 21rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.book-map-scroll {
			scroll-behavior: auto;
		}
	}
</style>
