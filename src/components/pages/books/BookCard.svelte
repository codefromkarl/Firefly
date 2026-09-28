<script lang="ts">
import type { BookCardData } from "@/types/book";
import { BOOK_SHELF_LABELS, BOOK_STATUS_LABELS } from "@/types/book";

interface Props {
	book: BookCardData;
	priority?: boolean;
}

const { book, priority = false }: Props = $props();
</script>

<!--
	两种排布：
	- 移动端（<sm）用横向紧凑条目：小封面 + 右侧文字，一本约占一屏的 1/6
	- sm 以上保持纵向大卡片（封面在上、信息在下）
	藏书量到百本级别后，移动端单列大卡会拉到上百屏，故按断点分流。
-->
<article
	class="group card-base overflow-hidden rounded-(--radius-large) border border-black/5 transition duration-300 hover:-translate-y-1 hover:shadow-lg dark:border-white/10 sm:h-full"
>
	<a
		href={book.url}
		class="flex h-full items-stretch gap-3 p-3 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-(--primary) sm:flex-col sm:gap-0 sm:p-0"
		aria-label={`查看《${book.title}》的书籍介绍`}
	>
		<div
			class="relative aspect-2/3 w-[5.5rem] shrink-0 overflow-hidden rounded-lg bg-(--btn-regular-bg) sm:w-full sm:rounded-none"
		>
			<img
				src={book.coverUrl}
				alt={`《${book.title}》封面`}
				width="480"
				height="720"
				loading={priority ? "eager" : "lazy"}
				fetchpriority={priority ? "high" : "auto"}
				decoding="async"
				class:list={[
					"h-full w-full object-cover transition duration-500",
					book.coverSource !== "placeholder" && "sm:group-hover:scale-105",
				]}
			/>
			<div
				class="absolute inset-x-0 bottom-0 hidden h-1/3 bg-linear-to-t from-black/70 to-transparent sm:block"
				aria-hidden="true"
			></div>
			<!-- 状态徽章：移动端放在文字区，避免压住小封面 -->
			<div class="absolute bottom-3 left-3 right-3 hidden flex-wrap gap-2 sm:flex">
				<span
					class="rounded-full bg-(--primary) px-2.5 py-1 text-xs font-semibold text-white shadow-sm dark:text-black/80"
				>
					{BOOK_STATUS_LABELS[book.status]}
				</span>
				{#if book.coverSource === "placeholder"}
					<span
						class="rounded-full bg-black/60 px-2.5 py-1 text-xs font-medium text-white"
					>
						封面待补
					</span>
				{/if}
			</div>
		</div>

		<div class="flex min-w-0 grow flex-col sm:p-5">
			<div class="flex flex-wrap items-center gap-2 sm:hidden">
				<span
					class="rounded-full bg-(--primary) px-2 py-0.5 text-[11px] font-semibold text-white dark:text-black/80"
				>
					{BOOK_STATUS_LABELS[book.status]}
				</span>
				<span
					class="rounded-full bg-(--primary)/10 px-2 py-0.5 text-[11px] font-medium text-(--primary)"
				>
					{BOOK_SHELF_LABELS[book.shelf]}
				</span>
			</div>

			<h2
				class="text-base font-bold leading-snug text-neutral-900 transition group-hover:text-(--primary) dark:text-neutral-100 sm:text-xl"
			>
				{book.title}
			</h2>
			{#if book.originalTitle}
				<p class="mt-1 line-clamp-1 text-xs text-neutral-400">
					{book.originalTitle}
				</p>
			{/if}
			<p class="mt-1.5 text-sm text-neutral-500 dark:text-neutral-400 sm:mt-2">
				{book.authors.join("、")}
			</p>

			<p
				class="mt-2 line-clamp-2 text-sm leading-6 text-neutral-600 dark:text-neutral-300 sm:mt-4 sm:line-clamp-3"
			>
				{book.description}
			</p>
			<p class="mt-1 text-xs text-neutral-400 max-sm:hidden">内容概述（自撰）</p>

			<div class="mt-auto hidden flex-wrap gap-1.5 pt-5 sm:flex">
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
