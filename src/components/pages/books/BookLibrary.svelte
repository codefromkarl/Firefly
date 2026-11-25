<script lang="ts">
import { onMount } from "svelte";
import {
	BOOK_SHELF_LABELS,
	BOOK_SHELF_VALUES,
	BOOK_STATUS_LABELS,
	BOOK_STATUS_VALUES,
	type BookCardData,
	type BookShelf,
	type BookStatus,
} from "@/types/book";
import { uniqueBookListings } from "@/utils/book-listings";
import { replaceBookUrl } from "@/utils/book-navigation";
import BookCard from "./BookCard.svelte";

let { books }: { books: BookCardData[] } = $props();
let domain = $state("");
let query = $state("");
let status = $state<BookStatus | "">("");
let legacy = $state<BookShelf | "">("");
let limit = $state(48);
const domains = $derived(
	[...new Set(books.flatMap((b) => b.domains))].sort((a, b) =>
		a.localeCompare(b, "zh-CN"),
	),
);
const term = $derived(query.trim().toLocaleLowerCase("zh-CN"));
const total = $derived(uniqueBookListings(books).length);
const matches = $derived(
	uniqueBookListings(
		books.filter(
			(b) =>
				(!domain || b.domains.includes(domain)) &&
				(!legacy || b.shelf === legacy) &&
				(!status || b.status === status) &&
				(!term ||
					[
						b.title,
						b.originalTitle,
						...b.authors,
						b.description,
						b.question,
						...b.domains,
						...b.topics,
					]
						.join(" ")
						.toLocaleLowerCase("zh-CN")
						.includes(term)),
		),
	),
);
function restore() {
	const p = new URL(location.href).searchParams;
	domain = domains.find((d) => d === p.get("domain")) ?? "";
	status = BOOK_STATUS_VALUES.find((s) => s === p.get("status")) ?? "";
	legacy =
		BOOK_SHELF_VALUES.find(
			(s) =>
				s ===
				(p.get("shelf") ?? (p.get("view") === "free" ? p.get("genre") : null)),
		) ?? "";
	query = p.get("q") ?? "";
	limit = 48;
}
function sync() {
	const u = new URL(location.href);
	for (const k of ["view", "level", "field", "genre", "topic"])
		u.searchParams.delete(k);
	for (const [k, v] of Object.entries({
		domain,
		status,
		shelf: legacy,
		q: query.trim(),
	})) {
		if (v) u.searchParams.set(k, v);
		else u.searchParams.delete(k);
	}
	limit = 48;
	replaceBookUrl(u);
}
function choose(d: string) {
	domain = d;
	legacy = "";
	sync();
}
function clear() {
	domain = "";
	query = "";
	legacy = "";
	status = "";
	sync();
}
onMount(() => {
	restore();
	const path = location.pathname;
	const pop = () => {
		if (location.pathname === path) restore();
	};
	window.addEventListener("popstate", pop);
	return () => window.removeEventListener("popstate", pop);
});
</script>
<section id="reading-guide" class="text-neutral-900 dark:text-neutral-100">
	<header><p class="kicker">Karl 的书架</p><h2>书单</h2><p class="lede">按领域找书。附有问题原文与传播线索的书目优先显示。</p></header>
	<div class="paper">
		<nav class="domains" aria-label="学科领域">
			<button aria-pressed={!domain&&!legacy} onclick={()=>choose("")}>全部 <small>{total}</small></button>
			{#each domains as d}<button aria-pressed={domain===d} onclick={()=>choose(d)}>{d}</button>{/each}
		</nav>
		<div class="tools">
			<label>搜索书单<input id="book-search" type="search" placeholder="书名、作者、问题或标签" bind:value={query} oninput={sync}/></label>
			<label>阅读状态<select id="book-status-filter" bind:value={status} onchange={sync}><option value="">全部状态</option>{#each BOOK_STATUS_VALUES as s}<option value={s}>{BOOK_STATUS_LABELS[s]}</option>{/each}</select></label>
		</div>
		<div class="results"><h3 aria-live="polite">{domain||(legacy?BOOK_SHELF_LABELS[legacy]:"全部书籍")} <small>· {matches.length} 本</small></h3>
			{#if query||domain||legacy||status}<button onclick={clear}>清除筛选</button>{/if}
		</div>
		{#each matches.slice(0,limit) as b,i (b.id)}<BookCard book={b} onDomain={choose} priority={i===0}/>{:else}<p class="empty">没有匹配的书籍。换个关键词，或清除筛选后再试。</p>{/each}
		{#if matches.length>limit}<button class="more" onclick={()=>limit+=48}>加载更多（已显示 {limit} / {matches.length}）</button>{/if}
	</div>
</section>
<style>
	#reading-guide{max-width:66rem;margin:auto;padding:0 .35rem}
	header{padding:1.4rem 0}.kicker{color:var(--btn-content);font-size:.82rem;font-weight:600}
	h2{font:650 clamp(2.3rem,5vw,3.4rem)/1.35 "Noto Serif SC","Songti SC",serif}.lede,.results small{color:var(--content-meta)}
	.paper{background:var(--card-bg);border-radius:var(--radius-large);padding:clamp(1rem,3vw,2.3rem)}
	.domains{display:flex;flex-wrap:wrap;gap:.2rem .4rem}.domains button{padding:.42rem .75rem;border-radius:.4rem;font-size:.94rem}
	button{cursor:pointer}.domains button[aria-pressed=true],.more{background:var(--btn-regular-bg);color:var(--btn-content);font-weight:650}
	.tools{display:flex;gap:1rem;margin:1rem 0 1.4rem;border-top:1px solid var(--line-divider);padding-top:1rem}
	.tools label{display:grid;gap:.35rem;font-size:.82rem;color:var(--content-meta)}.tools label:first-child{flex:1;min-width:0}
	input,select{width:100%;min-height:44px;border:1px solid var(--meta-divider);border-radius:.45rem;padding:.4rem .6rem;background:var(--card-bg);color:inherit;font-size:.95rem}
	.results{display:flex;justify-content:space-between;align-items:center;padding-bottom:.8rem}.results h3{font-weight:650}.results button{font-size:.86rem;color:var(--btn-content)}
	.more{display:block;margin:1rem auto 0;padding:.7rem 1.2rem;border-radius:.5rem}.empty{padding:2rem 0;color:var(--content-meta)}
	@media(max-width:600px){header{padding:.5rem 0 1rem}.tools{gap:.5rem}.domains{gap:0}.domains button{font-size:.85rem;padding:.35rem .55rem;min-height:44px}}
</style>
