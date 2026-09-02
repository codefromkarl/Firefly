<script lang="ts">
import type { BookCardData } from "@/types/book";
import { BOOK_SHELF_LABELS, BOOK_STATUS_LABELS } from "@/types/book";

interface Props {
	book: BookCardData;
	priority?: boolean;
}

const { book, priority = false }: Props = $props();

const topicLine = book.topics.slice(0, 3).join(" / ");
const MONO =
	"'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
</script>

<article
	class="group relative flex h-full flex-col overflow-hidden rounded-(--radius-md) border border-(--line-divider) bg-(--card-bg) transition duration-300 hover:-translate-y-0.5 hover:border-(--meta-divider)"
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
				class="h-full w-full object-cover"
			/>
			<div
				class="absolute inset-x-0 bottom-0 h-1/4 bg-linear-to-t from-black/65 to-transparent"
				aria-hidden="true"
			></div>
			<span
				class="absolute left-3 top-3 rounded-sm border border-white/15 bg-black/55 px-2 py-1 text-[0.65rem] font-semibold tracking-[0.1em] text-white/95 backdrop-blur-sm"
			>
				{BOOK_STATUS_LABELS[book.status]}
			</span>
		</div>

		<div class="flex grow flex-col px-4.5 pb-4.5 pt-4">
			<h2
				class="line-clamp-2 text-[1.05rem] font-bold leading-snug tracking-[-0.01em] text-90 transition group-hover:text-(--primary)"
			>
				{book.title}
			</h2>
			{#if book.originalTitle}
				<p
					class="mt-1.5 line-clamp-1 text-[0.7rem] tracking-[0.06em] text-50"
					style={`font-family: ${MONO}`}
				>
					{book.originalTitle}
				</p>
			{/if}
			<p class="mt-2 text-xs text-50">{book.authors.join("、")}</p>

			<p class="mt-3 line-clamp-2 text-[0.82rem] leading-relaxed text-75">
				{book.sourceIntroduction}
			</p>

			<div class="hairline-t mt-auto flex items-baseline gap-2.5 pt-3.5">
				<span class="shrink-0 text-[0.7rem] font-semibold text-(--primary)">
					{BOOK_SHELF_LABELS[book.shelf]}
				</span>
				{#if topicLine}
					<span
						class="line-clamp-1 text-[0.68rem] tracking-[0.04em] text-50"
						style={`font-family: ${MONO}`}
					>
						{topicLine}
					</span>
				{/if}
			</div>
		</div>
	</a>
</article>
