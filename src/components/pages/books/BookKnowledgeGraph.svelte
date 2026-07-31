<script lang="ts">
import type { Core, Stylesheet } from "cytoscape";
import { onMount, tick } from "svelte";
import type {
	BookGraphData,
	BookGraphNodeKind,
	BookGraphRelation,
} from "@/types/book";
import {
	BOOK_GRAPH_BASIS_LABELS,
	BOOK_GRAPH_NODE_KIND_LABELS,
	BOOK_GRAPH_RELATION_LABELS,
	BOOK_GRAPH_STAGE_LABELS,
} from "@/types/book";
import BookGraphEvidence from "./BookGraphEvidence.svelte";
import BookGraphOverview from "./BookGraphOverview.svelte";

interface Props {
	graph: BookGraphData;
}

const { graph }: Props = $props();

type GraphView = "overview" | "relations" | "list";

const stageDisclosure = {
	preview: "这是预读地图，不代表站长已读或认同书中观点。",
	reading: "这是阅读中地图，内容与结构会随阅读和来源复核继续调整。",
	reviewed: "这是复核后的正式知识图谱，仍应结合页面标注的来源理解。",
} satisfies Record<BookGraphData["stage"], string>;

let graphContainer: HTMLDivElement;
let cy: Core | undefined;
let startGraphInitialization: (() => Promise<void>) | undefined;
let ready = $state(false);
let loadError = $state("");
let selectedNodeId = $state<string | null>(null);
let activeView = $state<GraphView>("overview");
const overviewLabel = graph.bookMap ? "全书主线" : "结构概览";

const nodeKinds = [
	...new Set(graph.nodes.map((node) => node.kind)),
] as BookGraphNodeKind[];
const relationKinds = [
	...new Set(graph.edges.map((edge) => edge.relation)),
] as BookGraphRelation[];

let visibleNodeKinds = $state<BookGraphNodeKind[]>([...nodeKinds]);
let visibleRelationKinds = $state<BookGraphRelation[]>([...relationKinds]);

const selectedNode = $derived(
	graph.nodes.find((node) => node.id === selectedNodeId) ?? null,
);
const selectedEdges = $derived(
	selectedNode
		? graph.edges.filter(
				(edge) =>
					edge.source === selectedNode.id || edge.target === selectedNode.id,
			)
		: [],
);

function resolveCssColor(value: string, fallback: string): string {
	const probe = document.createElement("span");
	probe.style.color = value;
	probe.style.position = "fixed";
	probe.style.opacity = "0";
	probe.style.pointerEvents = "none";
	document.body.append(probe);
	const resolved = getComputedStyle(probe).color || fallback;
	probe.remove();
	return resolved;
}

function createGraphStyles(): Stylesheet[] {
	const root = document.documentElement;
	const isDark =
		root.dataset.theme === "dark" || root.classList.contains("dark");
	const text = resolveCssColor(
		"var(--text-90)",
		isDark ? "rgb(245 245 245)" : "rgb(30 30 30)",
	);
	const panel = resolveCssColor(
		"var(--card-bg)",
		isDark ? "rgb(38 38 42)" : "rgb(255 255 255)",
	);
	const line = isDark ? "#73737f" : "#8c8c99";

	return [
		{
			selector: "node",
			style: {
				"background-color": "#64748b",
				"border-color": panel,
				"border-width": 2,
				color: text,
				"font-family": "inherit",
				"font-size": 11,
				height: "mapData(importance, 1, 3, 34, 54)",
				label: "data(label)",
				"text-background-color": panel,
				"text-background-opacity": 0.88,
				"text-background-padding": 3,
				"text-background-shape": "roundrectangle",
				"text-max-width": 120,
				"text-valign": "bottom",
				"text-wrap": "wrap",
				width: "mapData(importance, 1, 3, 34, 54)",
			},
		},
		{
			selector: 'node[kind = "core"]',
			style: {
				"background-color": isDark ? "#c4b5fd" : "#7c3aed",
				shape: "diamond",
			},
		},
		{
			selector: 'node[kind = "chapter"]',
			style: {
				"background-color": isDark ? "#93c5fd" : "#2563eb",
				shape: "round-rectangle",
			},
		},
		{
			selector: 'node[kind = "model"]',
			style: {
				"background-color": isDark ? "#67e8f9" : "#0891b2",
				shape: "hexagon",
			},
		},
		{
			selector: 'node[kind = "bias"]',
			style: {
				"background-color": isDark ? "#fda4af" : "#e11d48",
				shape: "triangle",
			},
		},
		{
			selector: 'node[kind = "practice"]',
			style: {
				"background-color": isDark ? "#86efac" : "#16a34a",
				shape: "round-tag",
			},
		},
		{
			selector: 'node[kind = "outcome"]',
			style: {
				"background-color": isDark ? "#fdba74" : "#ea580c",
				shape: "star",
			},
		},
		{
			selector: "edge",
			style: {
				"curve-style": "bezier",
				"font-family": "inherit",
				"font-size": 9,
				label: "data(relationLabel)",
				"line-color": line,
				"target-arrow-color": line,
				"target-arrow-shape": "none",
				"text-background-color": panel,
				"text-background-opacity": 0.85,
				"text-background-padding": 2,
				"text-rotation": "autorotate",
				width: 1.5,
			},
		},
		{
			selector: "edge[?directed]",
			style: {
				"target-arrow-shape": "triangle",
			},
		},
		{
			selector: ".filtered",
			style: {
				display: "none",
			},
		},
		{
			selector: ".dimmed",
			style: {
				opacity: 0.14,
				"text-opacity": 0,
			},
		},
		{
			selector: ".highlighted",
			style: {
				"border-width": 4,
				opacity: 1,
				"text-opacity": 1,
				width: 3,
			},
		},
		{
			selector: "node:selected",
			style: {
				"border-color": isDark ? "#ffffff" : "#111827",
				"border-width": 5,
			},
		},
	];
}

function applyGraphState() {
	if (!cy) return;

	cy.batch(() => {
		cy?.elements().removeClass("filtered dimmed highlighted");

		cy?.nodes().forEach((node) => {
			if (!visibleNodeKinds.includes(node.data("kind") as BookGraphNodeKind)) {
				node.addClass("filtered");
			}
		});

		cy?.edges().forEach((edge) => {
			if (
				!visibleRelationKinds.includes(
					edge.data("relation") as BookGraphRelation,
				)
			) {
				edge.addClass("filtered");
			}
		});

		if (!selectedNodeId) return;
		const node = cy?.getElementById(selectedNodeId);
		if (!node || node.empty() || node.hasClass("filtered")) {
			selectedNodeId = null;
			return;
		}

		const visibleElements = cy?.elements().not(".filtered");
		visibleElements?.addClass("dimmed");
		const neighborhood = node.closedNeighborhood().not(".filtered");
		neighborhood.removeClass("dimmed").addClass("highlighted");
		node.select();
	});
}

function selectNode(nodeId: string | null) {
	selectedNodeId = nodeId;
	if (!cy) return;
	cy.nodes().unselect();
	applyGraphState();
}

function toggleNodeKind(kind: BookGraphNodeKind) {
	visibleNodeKinds = visibleNodeKinds.includes(kind)
		? visibleNodeKinds.filter((item) => item !== kind)
		: [...visibleNodeKinds, kind];
}

function toggleRelation(relation: BookGraphRelation) {
	visibleRelationKinds = visibleRelationKinds.includes(relation)
		? visibleRelationKinds.filter((item) => item !== relation)
		: [...visibleRelationKinds, relation];
}

function fitGraph() {
	if (!cy) return;
	const visibleElements = cy.elements().not(".filtered");
	if (visibleElements.nonempty()) cy.fit(visibleElements, 42);
}

function zoomGraph(factor: number) {
	if (!cy) return;
	const nextZoom = Math.min(
		cy.maxZoom(),
		Math.max(cy.minZoom(), cy.zoom() * factor),
	);
	cy.zoom({
		level: nextZoom,
		renderedPosition: {
			x: cy.width() / 2,
			y: cy.height() / 2,
		},
	});
}

async function selectView(view: GraphView) {
	activeView = view;
	if (view !== "relations") return;

	await tick();
	await startGraphInitialization?.();
	requestAnimationFrame(() => {
		cy?.resize();
		fitGraph();
	});
}

async function exploreNode(nodeId: string) {
	selectNode(nodeId);
	await selectView("relations");
}

$effect(() => {
	visibleNodeKinds;
	visibleRelationKinds;
	if (cy) applyGraphState();
});

onMount(() => {
	let disposed = false;
	let initializationStarted = false;
	let resizeObserver: ResizeObserver | undefined;
	let themeObserver: MutationObserver | undefined;
	let resizeFrame = 0;

	async function initializeGraph() {
		if (initializationStarted) return;
		initializationStarted = true;
		try {
			const { default: cytoscape } = await import("cytoscape");
			if (disposed) return;

			cy = cytoscape({
				container: graphContainer,
				elements: [
					...graph.nodes.map((node) => ({
						data: { ...node },
					})),
					...graph.edges.map((edge) => ({
						data: {
							...edge,
							relationLabel: BOOK_GRAPH_RELATION_LABELS[edge.relation],
						},
					})),
				],
				style: createGraphStyles(),
				layout: {
					name: graph.layout,
					animate: false,
					fit: true,
					padding: 42,
				},
				minZoom: 0.35,
				maxZoom: 2.5,
				wheelSensitivity: 0.18,
			});

			cy.on("tap", "node", (event) => {
				selectNode(event.target.id());
			});
			cy.on("tap", (event) => {
				if (event.target === cy) selectNode(null);
			});

			resizeObserver = new ResizeObserver(() => {
				cancelAnimationFrame(resizeFrame);
				resizeFrame = requestAnimationFrame(() => cy?.resize());
			});
			resizeObserver.observe(graphContainer);

			themeObserver = new MutationObserver(() => {
				if (!cy) return;
				cy.style().fromJson(createGraphStyles()).update();
				applyGraphState();
			});
			themeObserver.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ["class", "data-theme"],
			});

			ready = true;
		} catch (error) {
			console.error("[BookKnowledgeGraph] 图谱加载失败:", error);
			loadError = "交互图谱暂时无法加载，请使用下方结构列表浏览内容。";
		}
	}

	startGraphInitialization = initializeGraph;

	return () => {
		disposed = true;
		startGraphInitialization = undefined;
		cancelAnimationFrame(resizeFrame);
		resizeObserver?.disconnect();
		themeObserver?.disconnect();
		cy?.destroy();
		cy = undefined;
	};
});
</script>

<section
	class="book-knowledge-graph"
	aria-labelledby="book-graph-heading"
	data-pagefind-body
>
	<div class="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
		<div>
			<p class="text-sm font-semibold tracking-wide text-(--primary)">KNOWLEDGE MAP</p>
			<h2 id="book-graph-heading" class="mt-1 text-2xl font-bold text-neutral-900 dark:text-neutral-100">
				{graph.title}
			</h2>
			<p class="mt-2 max-w-3xl leading-7 text-neutral-600 dark:text-neutral-300">
				{graph.summary}
			</p>
		</div>
		<div class="flex shrink-0 flex-wrap gap-2">
			<span class="rounded-full bg-(--primary)/12 px-3 py-1.5 text-xs font-semibold text-(--primary)">
				{BOOK_GRAPH_STAGE_LABELS[graph.stage]}
			</span>
			{#if graph.aiAssisted}
				<span class="rounded-full bg-amber-500/12 px-3 py-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300">
					AI 辅助整理
				</span>
			{/if}
		</div>
	</div>

	<div class="mb-5 rounded-xl border border-(--line-divider) bg-(--btn-regular-bg)/55 px-4 py-3">
		<p class="text-sm leading-6 text-neutral-600 dark:text-neutral-300">
			<strong class="text-neutral-800 dark:text-neutral-100">内容依据：</strong>
			{graph.basis.map((basis) => BOOK_GRAPH_BASIS_LABELS[basis]).join("、")}。
			页面以重新组织的短总结为主；来源位置用于复核，原文只在存在经核对的短摘录时按需展开。
			{stageDisclosure[graph.stage]}
		</p>
	</div>

	<div
		class="mb-5 flex flex-wrap gap-2 rounded-xl bg-(--btn-regular-bg) p-1.5"
		role="tablist"
		aria-label="知识地图阅读方式"
	>
		{#each [
			{ id: "overview", label: overviewLabel },
			{ id: "relations", label: "关系探索" },
			{ id: "list", label: "结构列表" },
		] as view}
			<button
				type="button"
				role="tab"
				aria-selected={activeView === view.id}
				aria-controls={`graph-${view.id}-panel`}
				onclick={() => selectView(view.id as GraphView)}
				class:list={[
					"rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary)",
					activeView === view.id
						? "bg-(--card-bg) text-(--primary) shadow-sm"
						: "text-neutral-500 hover:text-(--primary) dark:text-neutral-400",
				]}
			>
				{view.label}
			</button>
		{/each}
	</div>

	<div
		id="graph-overview-panel"
		role="tabpanel"
		hidden={activeView !== "overview"}
	>
		<BookGraphOverview {graph} />
	</div>

	<div
		id="graph-relations-panel"
		role="tabpanel"
		hidden={activeView !== "relations"}
	>
		<div class="mb-4 grid gap-3 lg:grid-cols-2">
			<details class="rounded-xl border border-(--line-divider) bg-(--card-bg) p-3" open>
				<summary class="cursor-pointer text-sm font-semibold text-neutral-800 dark:text-neutral-100">
					节点类型
				</summary>
				<div class="mt-3 flex flex-wrap gap-2">
					{#each nodeKinds as kind}
						<label class="flex cursor-pointer items-center gap-2 rounded-lg bg-(--btn-regular-bg) px-3 py-2 text-sm">
							<input
								type="checkbox"
								checked={visibleNodeKinds.includes(kind)}
								onchange={() => toggleNodeKind(kind)}
								class="accent-(--primary)"
							/>
							<span>{BOOK_GRAPH_NODE_KIND_LABELS[kind]}</span>
						</label>
					{/each}
				</div>
			</details>

			<details class="rounded-xl border border-(--line-divider) bg-(--card-bg) p-3">
				<summary class="cursor-pointer text-sm font-semibold text-neutral-800 dark:text-neutral-100">
					关系类型
				</summary>
				<div class="mt-3 flex flex-wrap gap-2">
					{#each relationKinds as relation}
						<label class="flex cursor-pointer items-center gap-2 rounded-lg bg-(--btn-regular-bg) px-3 py-2 text-sm">
							<input
								type="checkbox"
								checked={visibleRelationKinds.includes(relation)}
								onchange={() => toggleRelation(relation)}
								class="accent-(--primary)"
							/>
							<span>{BOOK_GRAPH_RELATION_LABELS[relation]}</span>
						</label>
					{/each}
				</div>
			</details>
		</div>

		<div class="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(17rem,0.75fr)]">
			<div class="overflow-hidden rounded-xl border border-(--line-divider) bg-(--card-bg)">
				<div class="flex flex-wrap items-center gap-2 border-b border-(--line-divider) px-3 py-2">
					<button
						type="button"
						onclick={() => zoomGraph(1.2)}
						disabled={!ready}
						class="graph-control"
						aria-label="放大图谱"
					>
						放大
					</button>
					<button
						type="button"
						onclick={() => zoomGraph(1 / 1.2)}
						disabled={!ready}
						class="graph-control"
						aria-label="缩小图谱"
					>
						缩小
					</button>
					<button
						type="button"
						onclick={fitGraph}
						disabled={!ready}
						class="graph-control"
					>
						适配视图
					</button>
					<button
						type="button"
						onclick={() => selectNode(null)}
						disabled={!ready || !selectedNode}
						class="graph-control"
					>
						清除选择
					</button>
					<span class="ml-auto text-xs text-neutral-400">
						拖动画布 · 滚轮或双指缩放
					</span>
				</div>

				<div
					bind:this={graphContainer}
					class="graph-canvas"
					role="img"
					aria-label={`${graph.title}，包含 ${graph.nodes.length} 个节点和 ${graph.edges.length} 条关系`}
				>
					{#if !ready && !loadError}
						<div class="flex h-full items-center justify-center text-sm text-neutral-400">
							正在加载交互图谱…
						</div>
					{/if}
				</div>

				{#if loadError}
					<p class="border-t border-(--line-divider) px-4 py-3 text-sm text-amber-700 dark:text-amber-300" role="status">
						{loadError}
					</p>
				{/if}
			</div>

			<aside
				class="rounded-xl border border-(--line-divider) bg-(--card-bg) p-5"
				aria-live="polite"
				aria-atomic="true"
			>
				{#if selectedNode}
					<p class="text-xs font-semibold text-(--primary)">
						{BOOK_GRAPH_NODE_KIND_LABELS[selectedNode.kind]}
					</p>
					<h3 class="mt-1 text-xl font-bold text-neutral-900 dark:text-neutral-100">
						{selectedNode.label}
					</h3>
					<p class="mt-3 leading-7 text-neutral-600 dark:text-neutral-300">
						{selectedNode.summary}
					</p>
					<BookGraphEvidence
						provenance={selectedNode.provenance}
						sourceRefs={selectedNode.sourceRefs}
					/>
					{#if selectedNode.chapter}
						<p class="mt-4 text-sm text-neutral-500 dark:text-neutral-400">
							相关章节：{selectedNode.chapter}
						</p>
					{/if}
					{#if selectedNode.anchor}
						<a
							href={`#${selectedNode.anchor}`}
							class="mt-3 inline-flex rounded-lg bg-(--primary) px-4 py-2 text-sm font-semibold text-white transition hover:opacity-85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary) dark:text-black/80"
						>
							前往相关章节
						</a>
					{/if}

					{#if selectedEdges.length > 0}
						<h4 class="mt-6 text-sm font-semibold text-neutral-800 dark:text-neutral-100">
							直接关系
						</h4>
						<ul class="mt-2 space-y-2 text-sm text-neutral-600 dark:text-neutral-300">
							{#each selectedEdges as edge}
								<li class="rounded-lg bg-(--btn-regular-bg) px-3 py-2">
									<p>
										{graph.nodes.find((node) => node.id === edge.source)?.label}
										<span class="mx-1 text-(--primary)">
											{BOOK_GRAPH_RELATION_LABELS[edge.relation]}
										</span>
										{graph.nodes.find((node) => node.id === edge.target)?.label}
									</p>
									<BookGraphEvidence
										provenance={edge.provenance}
										sourceRefs={edge.sourceRefs}
									/>
								</li>
							{/each}
						</ul>
					{/if}
				{:else}
					<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100">
						选择一个节点
					</h3>
					<p class="mt-2 leading-7 text-neutral-600 dark:text-neutral-300">
						点击图中的节点或下方结构列表，可以查看概念说明并高亮它的一阶关系。
					</p>
					<div class="mt-5 grid grid-cols-2 gap-3 text-center text-sm">
						<div class="rounded-xl bg-(--btn-regular-bg) px-3 py-4">
							<strong class="block text-xl text-neutral-900 dark:text-neutral-100">{graph.nodes.length}</strong>
							<span class="text-neutral-500 dark:text-neutral-400">节点</span>
						</div>
						<div class="rounded-xl bg-(--btn-regular-bg) px-3 py-4">
							<strong class="block text-xl text-neutral-900 dark:text-neutral-100">{graph.edges.length}</strong>
							<span class="text-neutral-500 dark:text-neutral-400">关系</span>
						</div>
					</div>
				{/if}
			</aside>
		</div>
	</div>

	<details
		id="graph-list-panel"
		role="tabpanel"
		class="mt-5 rounded-xl border border-(--line-divider) bg-(--card-bg) p-4"
		class:graph-list-only={activeView === "list"}
		open={activeView === "list"}
	>
		<summary class="cursor-pointer font-semibold text-neutral-800 dark:text-neutral-100">
			使用结构列表浏览
		</summary>
		<div class="mt-4 grid gap-5 lg:grid-cols-2">
			<div>
				<h3 class="text-sm font-semibold text-neutral-700 dark:text-neutral-200">节点</h3>
				<ul class="mt-2 grid items-start gap-2 sm:grid-cols-2">
					{#each graph.nodes as node}
						<li>
							<details
								class="rounded-lg border border-(--line-divider) px-3 py-2 text-sm"
							>
								<summary class="cursor-pointer font-semibold text-neutral-800 dark:text-neutral-100">
									{node.label}
									<span class="ml-1 text-xs font-normal text-neutral-400">
									{BOOK_GRAPH_NODE_KIND_LABELS[node.kind]}
									</span>
								</summary>
								<p class="mt-2 leading-6 text-neutral-600 dark:text-neutral-300">
									{node.summary}
								</p>
								<BookGraphEvidence
									provenance={node.provenance}
									sourceRefs={node.sourceRefs}
								/>
								<button
									type="button"
									onclick={() => exploreNode(node.id)}
									class="mt-3 rounded-lg bg-(--btn-regular-bg) px-3 py-2 text-xs font-semibold text-(--primary) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary)"
								>
									在关系图中查看
								</button>
							</details>
						</li>
					{/each}
				</ul>
			</div>
			<div>
				<h3 class="text-sm font-semibold text-neutral-700 dark:text-neutral-200">关系</h3>
				<ul class="mt-2 space-y-2 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
					{#each graph.edges as edge}
						<li class="rounded-lg bg-(--btn-regular-bg) px-3 py-2">
							{graph.nodes.find((node) => node.id === edge.source)?.label}
							<strong class="mx-1 text-(--primary)">
								{BOOK_GRAPH_RELATION_LABELS[edge.relation]}
							</strong>
							{graph.nodes.find((node) => node.id === edge.target)?.label}
							{#if edge.summary}
								<span class="mt-1 block text-xs text-neutral-400">{edge.summary}</span>
							{/if}
							<BookGraphEvidence
								provenance={edge.provenance}
								sourceRefs={edge.sourceRefs}
							/>
						</li>
					{/each}
				</ul>
			</div>
		</div>
	</details>
</section>

<style>
	.graph-canvas {
		height: clamp(28rem, 64vh, 44rem);
		min-width: 0;
	}

	.graph-control {
		border-radius: 0.6rem;
		background: var(--btn-regular-bg);
		padding: 0.45rem 0.75rem;
		font-size: 0.8rem;
		font-weight: 600;
		transition:
			opacity 0.2s,
			color 0.2s;
	}

	.graph-control:hover:not(:disabled),
	.graph-control:focus-visible {
		color: var(--primary);
	}

	.graph-control:focus-visible {
		outline: 2px solid var(--primary);
		outline-offset: 2px;
	}

	.graph-control:disabled {
		cursor: not-allowed;
		opacity: 0.4;
	}

	@media (max-width: 640px) {
		.graph-canvas {
			height: 30rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.book-knowledge-graph *,
		.book-knowledge-graph *::before,
		.book-knowledge-graph *::after {
			scroll-behavior: auto !important;
			transition-duration: 0.01ms !important;
		}
	}
</style>
