import { type CollectionEntry, getCollection } from "astro:content";
import type {
	BookCardData,
	BookDirectoryItem,
	BookGraphData,
} from "@/types/book";
import { url } from "@/utils/url-utils";

export async function getPublishedBooks(): Promise<CollectionEntry<"books">[]> {
	const books = await getCollection("books", ({ data }) =>
		import.meta.env.PROD ? data.draft !== true : true,
	);

	return books.sort((a, b) =>
		a.data.title.localeCompare(b.data.title, "zh-CN"),
	);
}

export async function getGraphForBook(
	book: CollectionEntry<"books">,
): Promise<CollectionEntry<"bookGraphs">> {
	const graphs = await getCollection("bookGraphs");
	const matches = graphs.filter((entry) => entry.data.book.id === book.id);

	if (matches.length !== 1) {
		throw new Error(
			`Expected exactly one graph for "${book.id}", found ${matches.length}`,
		);
	}

	const [graph] = matches;
	if (graph.id !== book.id) {
		throw new Error(
			`Book graph "${graph.id}" must be adjacent to its book "${book.id}"`,
		);
	}
	if (graph.data.stage !== book.data.graphStage) {
		throw new Error(
			`Book "${book.id}" and its graph must use the same graph stage`,
		);
	}

	return graph;
}

export function getBookUrl(bookId: string): string {
	return url(`/books/${bookId}/`);
}

export function toBookDirectoryItems(
	books: CollectionEntry<"books">[],
): BookDirectoryItem[] {
	return books.map((book) => ({
		id: book.id,
		title: book.data.title,
		shelf: book.data.shelf,
		url: getBookUrl(book.id),
	}));
}

export function toBookGraphData(
	entry: CollectionEntry<"bookGraphs">,
): BookGraphData {
	const { book: _book, ...graph } = entry.data;
	return graph;
}

export function toBookCardData(
	book: CollectionEntry<"books">,
	coverUrl: string,
): BookCardData {
	return {
		id: book.id,
		title: book.data.title,
		originalTitle: book.data.originalTitle,
		authors: book.data.authors,
		description: book.data.description,
		sourceIntroduction: book.data.introductions[0].text,
		status: book.data.status,
		shelf: book.data.shelf,
		topics: book.data.topics,
		coverUrl,
		url: getBookUrl(book.id),
	};
}
