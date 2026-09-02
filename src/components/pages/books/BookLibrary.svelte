<script lang="ts">
import { onMount } from "svelte";
import type { BookCardData, BookShelf, BookStatus } from "@/types/book";
import {
	BOOK_SHELF_LABELS,
	BOOK_SHELF_VALUES,
	BOOK_STATUS_LABELS,
	BOOK_STATUS_VALUES,
} from "@/types/book";
import Icon from "@/components/common/Icon.svelte";
import BookCard from "./BookCard.svelte";

interface Props {
	books: BookCardData[];
}

const { books }: Props = $props();

let query = $state("");
let activeShelf = $state<"all" | BookShelf>("all");
let activeStatus = $state<"all" | BookStatus>("all");
let activeTopic = $state("all");

const shelves = $derived(
	BOOK_SHELF_VALUES.filter((shelf) =>
		books.some((book) => book.shelf === shelf),
	),
);

const topics = $derived(
	[...new Set(books.flatMap((book) => book.topics))].sort((a, b) =>
		a.localeCompare(b, "zh-CN"),
	),
);

const normalizedQuery = $derived(query.trim().toLocaleLowerCase("zh-CN"));

const filteredBooks = $derived(
	books.filter((book) => {
		const matchesQuery =
			!normalizedQuery ||
			[book.title, book.originalTitle ?? "", ...book.authors, ...book.topics]
				.join(" ")
				.toLocaleLowerCase("zh-CN")
				.includes(normalizedQuery);
		const matchesShelf = activeShelf === "all" || book.shelf === activeShelf;
		const matchesStatus =
			activeStatus === "all" || book.status === activeStatus;
		const matchesTopic =
			activeTopic === "all" || book.topics.includes(activeTopic);

		return matchesQuery && matchesShelf && matchesStatus && matchesTopic;
	}),
);

const activeFilterLabels = $derived.by(() => {
	const labels: string[] = [];
	if (activeShelf !== "all") labels.push(BOOK_SHELF_LABELS[activeShelf]);
	if (activeStatus !== "all") labels.push(BOOK_STATUS_LABELS[activeStatus]);
	if (activeTopic !== "all") labels.push(`#${activeTopic}`);
	if (query.trim()) labels.push(`关键词：${query.trim()}`);
	return labels;
});

function isBookShelf(value: string | null): value is BookShelf {
	return BOOK_SHELF_VALUES.includes(value as BookShelf);
}

function isBookStatus(value: string | null): value is BookStatus {
	return BOOK_STATUS_VALUES.includes(value as BookStatus);
}

function readFiltersFromUrl() {
	const params = new URL(window.location.href).searchParams;
	const shelf = params.get("shelf");
	const status = params.get("status");
	const topic = params.get("topic");

	query = params.get("q") ?? "";
	activeShelf = isBookShelf(shelf) ? shelf : "all";
	activeStatus = isBookStatus(status) ? status : "all";
	activeTopic = topic && topics.includes(topic) ? topic : "all";
}

function updateDirectoryState() {
	const hasFilters = Boolean(
		query.trim() ||
			activeShelf !== "all" ||
			activeStatus !== "all" ||
			activeTopic !== "all",
	);
	document
		.querySelectorAll<HTMLAnchorElement>("[data-book-library-root]")
		.forEach((link) => {
			link.classList.toggle("book-directory-root-active", !hasFilters);
		});

	document
		.querySelectorAll<HTMLDetailsElement>("[data-book-shelf-group]")
		.forEach((group) => {
			const isFilteredShelf =
				activeShelf !== "all" && group.dataset.bookShelfGroup === activeShelf;
			group.classList.toggle("book-shelf-filtered", isFilteredShelf);
			if (isFilteredShelf) group.open = true;
		});
}

function writeFiltersToUrl() {
	const current = new URL(window.location.href);
	if (query.trim()) current.searchParams.set("q", query.trim());
	else current.searchParams.delete("q");
	if (activeShelf !== "all") current.searchParams.set("shelf", activeShelf);
	else current.searchParams.delete("shelf");
	if (activeStatus !== "all") current.searchParams.set("status", activeStatus);
	else current.searchParams.delete("status");
	if (activeTopic !== "all") current.searchParams.set("topic", activeTopic);
	else current.searchParams.delete("topic");

	history.replaceState(history.state, "", current);
	updateDirectoryState();
}

function handleQueryInput(event: Event) {
	query = (event.currentTarget as HTMLInputElement).value;
	writeFiltersToUrl();
}

function handleShelfChange(event: Event) {
	activeShelf = (event.currentTarget as HTMLSelectElement).value as
		| "all"
		| BookShelf;
	writeFiltersToUrl();
}

function handleStatusChange(event: Event) {
	activeStatus = (event.currentTarget as HTMLSelectElement).value as
		| "all"
		| BookStatus;
	writeFiltersToUrl();
}

function handleTopicChange(event: Event) {
	activeTopic = (event.currentTarget as HTMLSelectElement).value;
	writeFiltersToUrl();
}

function clearFilters() {
	query = "";
	activeShelf = "all";
	activeStatus = "all";
	activeTopic = "all";
	writeFiltersToUrl();
}

onMount(() => {
	readFiltersFromUrl();
	writeFiltersToUrl();

	const handlePopState = () => {
		readFiltersFromUrl();
		writeFiltersToUrl();
	};
	window.addEventListener("popstate", handlePopState);

	return () => {
		window.removeEventListener("popstate", handlePopState);
	};
});
</script>

<section aria-labelledby="book-library-heading">
	<div class="card-base mb-6 rounded-(--radius-large) p-5 md:p-6">
		<div class="flex flex-col gap-4">
			<div>
				<label
					for="book-search"
					class="mb-2 block text-sm font-semibold text-neutral-700 dark:text-neutral-200"
				>
					搜索书单
				</label>
				<div class="relative">
					<svg
						class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-400"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						aria-hidden="true"
					>
						<circle cx="11" cy="11" r="7"></circle>
						<path d="m20 20-3.5-3.5"></path>
					</svg>
					<input
						id="book-search"
						type="search"
						value={query}
						oninput={handleQueryInput}
						placeholder="搜索书名、作者或主题"
						class="w-full rounded-xl border border-(--line-divider) bg-(--card-bg) py-3 pl-10 pr-4 text-sm text-neutral-900 outline-none transition placeholder:text-neutral-400 focus:border-(--primary) focus:ring-2 focus:ring-(--primary)/20 dark:text-neutral-100"
					/>
				</div>
			</div>

			<div class="grid gap-4 md:grid-cols-3">
				<div>
					<label
						for="book-shelf-filter"
						class="mb-2 block text-sm font-semibold text-neutral-700 dark:text-neutral-200"
					>
						主分类
					</label>
					<select
						id="book-shelf-filter"
						value={activeShelf}
						onchange={handleShelfChange}
						class="w-full rounded-xl border border-(--line-divider) bg-(--card-bg) px-3 py-3 text-sm text-neutral-700 outline-none focus:border-(--primary) dark:text-neutral-200"
					>
						<option value="all">全部分类</option>
						{#each shelves as shelf}
							<option value={shelf}>{BOOK_SHELF_LABELS[shelf]}</option>
						{/each}
					</select>
				</div>

				<div>
					<label
						for="book-status-filter"
						class="mb-2 block text-sm font-semibold text-neutral-700 dark:text-neutral-200"
					>
						阅读状态
					</label>
					<select
						id="book-status-filter"
						value={activeStatus}
						onchange={handleStatusChange}
						class="w-full rounded-xl border border-(--line-divider) bg-(--card-bg) px-3 py-3 text-sm text-neutral-700 outline-none focus:border-(--primary) dark:text-neutral-200"
					>
						<option value="all">全部状态</option>
						{#each BOOK_STATUS_VALUES as status}
							<option value={status}>{BOOK_STATUS_LABELS[status]}</option>
						{/each}
					</select>
				</div>

				<div>
					<label
						for="book-topic-filter"
						class="mb-2 block text-sm font-semibold text-neutral-700 dark:text-neutral-200"
					>
						主题
					</label>
					<select
						id="book-topic-filter"
						value={activeTopic}
						onchange={handleTopicChange}
						class="w-full rounded-xl border border-(--line-divider) bg-(--card-bg) px-3 py-3 text-sm text-neutral-700 outline-none focus:border-(--primary) dark:text-neutral-200"
					>
						<option value="all">全部主题</option>
						{#each topics as topic}
							<option value={topic}>{topic}</option>
						{/each}
					</select>
				</div>
			</div>

			{#if activeFilterLabels.length > 0}
				<div class="flex flex-wrap items-center gap-2" aria-label="当前筛选条件">
					<span class="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
						当前筛选
					</span>
					{#each activeFilterLabels as label}
						<span
							class="rounded-full bg-(--primary)/10 px-2.5 py-1 text-xs font-medium text-(--primary)"
						>
							{label}
						</span>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<div class="mb-4 flex items-center justify-between gap-4">
		<div>
			<h2 id="book-library-heading" class="text-xl font-bold text-neutral-900 dark:text-neutral-100">
				想读书单
			</h2>
			<p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400" aria-live="polite">
				显示 {filteredBooks.length} / {books.length} 本
			</p>
		</div>
		{#if activeFilterLabels.length > 0}
			<button
				type="button"
				onclick={clearFilters}
				class="rounded-xl bg-(--btn-regular-bg) px-4 py-2 text-sm font-medium text-(--btn-content) transition hover:bg-(--btn-regular-bg-hover) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary)"
			>
				清除筛选
			</button>
		{/if}
	</div>

	{#if filteredBooks.length > 0}
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
			{#each filteredBooks as book, index (book.id)}
				<BookCard {book} priority={index === 0} />
			{/each}
		</div>
	{:else}
		<div class="card-base rounded-(--radius-large) px-6 py-16 text-center">
			<div
				class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-(--radius-md) border border-(--line-divider)"
				aria-hidden="true"
			>
				<Icon icon="lucide:search-x" class="w-6 h-6 text-50" />
			</div>
			<h3 class="text-lg font-semibold text-neutral-800 dark:text-neutral-100">没有匹配的书籍</h3>
			<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
				换一个关键词或清除筛选后再试。
			</p>
			<button
				type="button"
				onclick={clearFilters}
				class="mt-5 rounded-xl bg-(--primary) px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--primary) dark:text-black/80"
			>
				查看全部书籍
			</button>
		</div>
	{/if}
</section>
