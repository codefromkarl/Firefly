<script lang="ts">
import type { BookGraphData, BookGraphNode } from "@/types/book";
import { BOOK_GRAPH_NODE_KIND_LABELS } from "@/types/book";
import BookGraphEvidence from "./BookGraphEvidence.svelte";
import BookMapSpine from "./BookMapSpine.svelte";

interface Props {
	graph: BookGraphData;
}

interface GraphSection {
	id: string;
	label: string;
	nodes: BookGraphNode[];
}

const { graph }: Props = $props();
let expandedSections = $state<string[]>([]);

const coreNodes = graph.nodes.filter((node) => node.kind === "core");
const groupedNodes = new Map<string, BookGraphNode[]>();

for (const node of graph.nodes) {
	if (node.kind === "core") continue;
	const label = node.chapter ?? "其他核心概念";
	const nodes = groupedNodes.get(label) ?? [];
	nodes.push(node);
	groupedNodes.set(label, nodes);
}

const sections: GraphSection[] = [...groupedNodes.entries()].map(
	([label, nodes], index) => ({
		id: `graph-section-${index}`,
		label,
		nodes,
	}),
);

function visibleNodes(section: GraphSection): BookGraphNode[] {
	if (expandedSections.includes(section.id)) return section.nodes;
	const importantNodes = section.nodes.filter((node) => node.importance === 3);
	return importantNodes.length > 0 ? importantNodes : section.nodes.slice(0, 2);
}

function toggleSection(sectionId: string) {
	expandedSections = expandedSections.includes(sectionId)
		? expandedSections.filter((id) => id !== sectionId)
		: [...expandedSections, sectionId];
}
</script>

{#if graph.bookMap}
	<BookMapSpine bookMap={graph.bookMap} nodes={graph.nodes} />
{:else}
	<section aria-labelledby="graph-overview-heading">
	<div class="rounded-xl border border-(--line-divider) bg-(--btn-regular-bg)/40 p-4 md:p-5">
		<p class="text-xs font-semibold tracking-wide text-(--primary)">
			先理解全书骨架
		</p>
		<h3
			id="graph-overview-heading"
			class="mt-1 text-lg font-bold text-neutral-900 dark:text-neutral-100"
		>
			核心主题与章节脉络
		</h3>
		<p class="mt-2 text-sm leading-6 text-neutral-500 dark:text-neutral-400">
			默认只显示关键概念；按章节展开后再查看完整节点，关系方向请切换到“关系探索”。
		</p>
	</div>

	<div class="mt-4 grid gap-4">
		{#each coreNodes as node}
			<article
				class="rounded-xl border-2 border-(--primary)/45 bg-(--primary)/8 p-5"
			>
				<p class="text-xs font-semibold text-(--primary)">
					{BOOK_GRAPH_NODE_KIND_LABELS[node.kind]}
				</p>
				<h4 class="mt-1 text-xl font-bold text-neutral-900 dark:text-neutral-100">
					{node.label}
				</h4>
				<p class="mt-2 leading-7 text-neutral-600 dark:text-neutral-300">
					{node.summary}
				</p>
				<BookGraphEvidence
					provenance={node.provenance}
					sourceRefs={node.sourceRefs}
				/>
			</article>
		{/each}

		<div class="grid gap-4 lg:grid-cols-2">
			{#each sections as section}
				<section
					class="rounded-xl border border-(--line-divider) bg-(--card-bg) p-4 md:p-5"
					aria-labelledby={`${section.id}-heading`}
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-xs font-semibold tracking-wide text-(--primary)">
								章节 / 主题分区
							</p>
							<h4
								id={`${section.id}-heading`}
								class="mt-1 text-lg font-bold text-neutral-900 dark:text-neutral-100"
							>
								{section.label}
							</h4>
						</div>
						<span class="rounded-full bg-(--btn-regular-bg) px-2.5 py-1 text-xs text-neutral-500">
							{section.nodes.length} 个概念
						</span>
					</div>

					<ul class="mt-4 space-y-3">
						{#each visibleNodes(section) as node}
							<li class="rounded-lg bg-(--btn-regular-bg) p-3">
								<div class="flex flex-wrap items-center gap-2">
									<strong class="text-neutral-800 dark:text-neutral-100">
										{node.label}
									</strong>
									<span class="text-xs text-neutral-400">
										{BOOK_GRAPH_NODE_KIND_LABELS[node.kind]}
									</span>
								</div>
								<p class="mt-1.5 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
									{node.summary}
								</p>
								<BookGraphEvidence
									provenance={node.provenance}
									sourceRefs={node.sourceRefs}
								/>
							</li>
						{/each}
					</ul>

					{#if section.nodes.length > visibleNodes(section).length || expandedSections.includes(section.id)}
						<button
							type="button"
							onclick={() => toggleSection(section.id)}
							aria-expanded={expandedSections.includes(section.id)}
							class="mt-4 rounded-lg bg-(--btn-regular-bg) px-3 py-2 text-sm font-semibold text-(--primary) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary)"
						>
							{expandedSections.includes(section.id)
								? "收起次要概念"
								: `展开其余 ${section.nodes.length - visibleNodes(section).length} 个概念`}
						</button>
					{/if}
				</section>
			{/each}
		</div>
	</div>
	</section>
{/if}
