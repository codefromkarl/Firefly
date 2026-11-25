<script lang="ts">
import { BOOK_STATUS_LABELS, type BookCardData } from "@/types/book";

let {
	book,
	onDomain,
	priority = false,
}: {
	book: BookCardData;
	onDomain: (name: string) => void;
	priority?: boolean;
} = $props();
</script>

<article class="book">
	<a class="cover" href={book.url} aria-label={book.title}>
		<img src={book.coverUrl} alt="" width="88" height="124" loading={priority?"eager":"lazy"}/>
		{#if book.coverSource==="placeholder"}<small>封面待补</small>{/if}
	</a>
	<div class="copy">
		<h3><a href={book.url}>{book.title}</a></h3>
		<p class="author">{book.authors.join("、")} · {BOOK_STATUS_LABELS[book.status]}</p>
		{#if book.question}<a href={book.url+"#public-question"} class="question"><span class="cue">问题</span>{book.question}</a>{/if}
		<p class="description"><span class="cue">概述</span>{book.description}</p>
		<div class="tags">{#each book.domains as domain}<button type="button" onclick={()=>onDomain(domain)}>{domain}</button>{/each}</div>
	</div>
</article>
<style>
	.book{display:grid;grid-template-columns:clamp(3.6rem,8vw,6rem) minmax(0,1fr);align-items:start;gap:clamp(.85rem,2vw,1.6rem);padding:1.4rem 0;border-top:1px solid var(--line-divider)}
	.cover img{width:100%;height:auto;max-height:9rem;object-fit:contain;object-position:top}
	.cover small,.author{font-size:.82rem;color:var(--content-meta)}
	h3{font-family:"Noto Serif SC","Songti SC",serif;font-size:clamp(1.15rem,2vw,1.55rem);font-weight:650;line-height:1.4}
	.author{margin:.25rem 0 .65rem}.description{line-height:1.7;color:var(--content-meta);font-size:.95rem}
	.question{display:block;color:var(--btn-content);font-weight:600;margin:.5rem 0}
	.cue{display:inline-block;margin-right:.6rem;color:var(--content-meta);font-size:.74rem;font-weight:500}
	.tags{display:flex;gap:.35rem .75rem;flex-wrap:wrap;margin-top:.45rem}
	.tags button{color:var(--btn-content);font-size:.82rem;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
	h3 a:hover,.question:hover{text-decoration:underline}
	@media(pointer:coarse){.tags button{min-height:44px}}
</style>
