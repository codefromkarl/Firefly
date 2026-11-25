// Group only explicitly verified editions or inclusions, never similar titles.
export function uniqueBookListings<
	T extends { id: string; listedWith?: string },
>(books: readonly T[]): T[] {
	const entries = new Map<string, T>();
	for (const book of books) {
		const key = book.listedWith ?? book.id;
		if (!entries.has(key) || book.id === key) entries.set(key, book);
	}
	return [...entries.values()];
}
