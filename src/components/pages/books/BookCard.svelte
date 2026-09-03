<script lang="ts">
import type { BookCardData } from "@/types/book";
import { BOOK_SHELF_LABELS, BOOK_STATUS_LABELS } from "@/types/book";

interface Props {
	book: BookCardData;
	priority?: boolean;
}

const { book, priority = false }: Props = $props();
</script>

<article
	class="group card-base h-full overflow-hidden rounded-(--radius-large) border border-black/5 transition duration-300 hover:-translate-y-1 hover:shadow-lg dark:border-white/10"
>
	<a
		href={book.url}
		class="flex h-full flex-col focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-(--primary)"
		aria-label={`查看《${book.title}》的书籍介绍`}
	>
		<div class="relative aspect-2/3 overflow-hidden bg-(--btn-regular-bg)">
			<img
				src={book.coverUrl}
				alt={`《${book.title}》封面`}
				width="480"
				height="720"
				loading={priority ? "eager" : "lazy"}
				fetchpriority={priority ? "high" : "auto"}
				decoding="async"
				class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
			/>
			<div
				class="absolute inset-x-0 bottom-0 h-1/3 bg-linear-to-t from-black/70 to-transparent"
				aria-hidden="true"
			></div>
			<div class="absolute bottom-3 left-3 right-3 flex flex-wrap gap-2">
				<span
					class="rounded-full bg-(--primary) px-2.5 py-1 text-xs font-semibold text-white shadow-sm dark:text-black/80"
				>
					{BOOK_STATUS_LABELS[book.status]}
				</span>
			</div>
		</div>

		<div class="flex grow flex-col p-5">
			<h2
				class="text-xl font-bold text-neutral-900 transition group-hover:text-(--primary) dark:text-neutral-100"
			>
				{book.title}
			</h2>
			{#if book.originalTitle}
				<p class="mt-1 line-clamp-1 text-xs text-neutral-400">
					{book.originalTitle}
				</p>
			{/if}
			<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
				{book.authors.join("、")}
			</p>

			<p class="mt-4 line-clamp-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
				{book.sourceIntroduction}
			</p>

			<div class="mt-auto flex flex-wrap gap-1.5 pt-5">
				<span
					class="rounded-full bg-(--primary)/10 px-2.5 py-1 text-xs font-medium text-(--primary)"
				>
					{BOOK_SHELF_LABELS[book.shelf]}
				</span>
				{#each book.topics.slice(0, 3) as topic}
					<span
						class="rounded-full bg-black/5 px-2.5 py-1 text-xs text-neutral-500 dark:bg-white/10 dark:text-neutral-400"
					>
						#{topic}
					</span>
				{/each}
			</div>
		</div>
	</a>
</article>
