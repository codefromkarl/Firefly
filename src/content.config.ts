import { defineCollection, reference } from "astro:content";
import type { CollectionConfig, SchemaContext } from "astro/content/config";
import { glob } from "astro/loaders";
import { type ZodType, z } from "astro/zod";
import {
	BOOK_ARGUMENT_CARD_KIND_VALUES,
	BOOK_ARGUMENT_CONTEXT_VALUES,
	BOOK_GRAPH_BASIS_VALUES,
	BOOK_GRAPH_LAYOUT_VALUES,
	BOOK_GRAPH_NODE_KIND_VALUES,
	BOOK_GRAPH_PROVENANCE_VALUES,
	BOOK_GRAPH_RELATION_VALUES,
	BOOK_GRAPH_STAGE_VALUES,
	BOOK_MAP_ARCHETYPE_VALUES,
	BOOK_MAP_PART_MATURITY_VALUES,
	BOOK_MAP_PART_ROLE_VALUES,
	BOOK_MAP_TRANSITION_RELATION_VALUES,
	BOOK_READING_REASON_KIND_VALUES,
	BOOK_SHELF_VALUES,
	BOOK_STATUS_VALUES,
	type BookExcerpt,
	type BookGraphData,
	type BookGraphProvenance,
	type BookGraphSourceRef,
	type BookGraphStage,
	type BookReadingReason,
	type BookShelf,
	type BookSourceCitation,
	type BookStatus,
} from "@/types/book";

type PostData = {
	title: string;
	published: Date;
	updated?: Date;
	draft: boolean;
	description: string;
	image: string;
	tags: string[];
	category: string | null;
	lang: string;
	pinned: boolean;
	author: string;
	sourceLink: string;
	licenseName: string;
	licenseUrl: string;
	comment: boolean;
	password: string;
	passwordHint: string;
	prevTitle: string;
	prevSlug: string;
	nextTitle: string;
	nextSlug: string;
};

type DynamicData = {
	published: Date;
	pinned: boolean;
	location: string;
};

type BookData = {
	title: string;
	originalTitle?: string;
	authors: string[];
	description: string;
	introductions: BookSourceCitation[];
	readingReasons: BookReadingReason[];
	endorsements: BookSourceCitation[];
	excerpts: BookExcerpt[];
	status: BookStatus;
	shelf: BookShelf;
	topics: string[];
	language: string;
	isbn?: string;
	cover: z.infer<ReturnType<SchemaContext["image"]>>;
	draft: boolean;
	graphStage: BookGraphStage;
	published?: Date;
};

type BookGraphEntryData = BookGraphData & {
	book: {
		collection: "books";
		id: string;
	};
};

type ContentCollection<T> = CollectionConfig<
	ZodType<T>,
	ReturnType<typeof glob>
>;

const postsCollection: ContentCollection<PostData> = defineCollection({
	loader: glob({ pattern: "**/*.{md,mdx}", base: "./src/content/posts" }),
	schema: z.object({
		title: z.string(),
		published: z.date(),
		updated: z.date().optional(),
		draft: z.boolean().optional().default(false),
		description: z.string().optional().default(""),
		image: z.string().optional().default(""),
		tags: z.array(z.string()).optional().default([]),
		category: z.string().optional().nullable().default(""),
		lang: z.string().optional().default(""),
		pinned: z.boolean().optional().default(false),
		author: z.string().optional().default(""),
		sourceLink: z.string().optional().default(""),
		licenseName: z.string().optional().default(""),
		licenseUrl: z.string().optional().default(""),
		comment: z.boolean().optional().default(true),
		password: z.string().optional().default(""),
		passwordHint: z.string().optional().default(""),

		/* For internal use */
		prevTitle: z.string().default(""),
		prevSlug: z.string().default(""),
		nextTitle: z.string().default(""),
		nextSlug: z.string().default(""),
	}),
});

const specCollection: ContentCollection<Record<string, never>> =
	defineCollection({
		loader: glob({ pattern: "**/*.{md,mdx}", base: "./src/content/spec" }),
		schema: z.object({}),
	});

const dynamicCollection: ContentCollection<DynamicData> = defineCollection({
	loader: glob({ pattern: "**/*.md", base: "./src/content/dynamic" }),
	schema: z.object({
		published: z.date(),
		pinned: z.boolean().optional().default(false),
		location: z.string().optional().default(""),
	}),
});

const bookIdFromEntry = (entry: string) =>
	entry.replace(/\/index\.(?:md|mdx)$/i, "");

const bookGraphIdFromEntry = (entry: string) =>
	entry.replace(/\/graph\.json$/i, "");

const bookSchema = ({ image }: SchemaContext): ZodType<BookData> =>
	z.object({
		title: z.string().min(1),
		originalTitle: z.string().min(1).optional(),
		authors: z.array(z.string().min(1)).min(1),
		description: z.string().min(1),
		introductions: z
			.array(
				z.object({
					text: z.string().min(1).max(240),
					source: z.string().min(1).max(120),
					url: z.url(),
				}),
			)
			.min(1),
		readingReasons: z
			.array(
				z.object({
					title: z.string().min(1).max(60),
					kind: z.enum(BOOK_READING_REASON_KIND_VALUES),
					text: z.string().min(1).max(240),
					source: z.string().min(1).max(120),
					url: z.url(),
				}),
			)
			.min(2)
			.max(4)
			.superRefine((reasons, context) => {
				const kinds = new Set(reasons.map((reason) => reason.kind));
				if (kinds.size !== reasons.length) {
					context.addIssue({
						code: "custom",
						message:
							"readingReasons must cover distinct reader-value dimensions",
					});
				}
			}),
		endorsements: z
			.array(
				z.object({
					text: z.string().min(1).max(240),
					source: z.string().min(1).max(120),
					url: z.url(),
				}),
			)
			.max(3)
			.default([]),
		excerpts: z
			.array(
				z.object({
					text: z.string().min(1).max(240),
					source: z.string().min(1).max(120),
					url: z.url().optional(),
				}),
			)
			.default([]),
		status: z.enum(BOOK_STATUS_VALUES),
		shelf: z.enum(BOOK_SHELF_VALUES),
		topics: z.array(z.string().min(1)).min(1),
		language: z.string().min(2).default("zh-CN"),
		isbn: z.string().min(10).optional(),
		cover: image(),
		draft: z.boolean().optional().default(false),
		graphStage: z.enum(BOOK_GRAPH_STAGE_VALUES),
		published: z.date().optional(),
	});

const booksCollection: ContentCollection<BookData> = defineCollection({
	loader: glob({
		pattern: "**/index.{md,mdx}",
		base: "./src/content/books",
		generateId: ({ entry }) => bookIdFromEntry(entry),
	}),
	schema: bookSchema,
});

const graphSourceRefSchema = z.object({
	basis: z.enum(BOOK_GRAPH_BASIS_VALUES),
	locator: z.string().min(1),
	quote: z.string().min(1).max(240).optional(),
});

const graphNodeSchema = z.object({
	id: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
	label: z.string().min(1),
	kind: z.enum(BOOK_GRAPH_NODE_KIND_VALUES),
	summary: z.string().min(1),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).min(1),
	chapter: z.string().min(1).optional(),
	anchor: z
		.string()
		.regex(/^[^#\s]+$/, "anchor must not include # or whitespace")
		.optional(),
	importance: z.union([z.literal(1), z.literal(2), z.literal(3)]).default(2),
});

const graphEdgeSchema = z.object({
	id: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
	source: z.string().min(1),
	target: z.string().min(1),
	relation: z.enum(BOOK_GRAPH_RELATION_VALUES),
	directed: z.boolean().default(true),
	summary: z.string().min(1).optional(),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).optional(),
});

const bookMapStatementSchema = z.object({
	text: z.string().min(1),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).min(1),
});

const bookArgumentCardSchema = z.object({
	id: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
	kind: z.enum(BOOK_ARGUMENT_CARD_KIND_VALUES),
	title: z.string().min(1),
	summary: z.string().min(1),
	context: z.enum(BOOK_ARGUMENT_CONTEXT_VALUES),
	conceptNodeIds: z.array(z.string().min(1)).min(1),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).min(1),
});

const bookMapPartSchema = z.object({
	id: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
	order: z.number().int().positive(),
	title: z.string().min(1),
	role: z.enum(BOOK_MAP_PART_ROLE_VALUES),
	maturity: z.enum(BOOK_MAP_PART_MATURITY_VALUES).default("developed"),
	question: z.string().min(1),
	thesis: z.string().min(1),
	inputUnderstanding: z.string().min(1),
	outputUnderstanding: z.string().min(1),
	conceptNodeIds: z.array(z.string().min(1)).min(1),
	argumentCards: z.array(bookArgumentCardSchema).default([]),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).min(1),
});

const bookMapTransitionSchema = z.object({
	id: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
	source: z.string().min(1),
	target: z.string().min(1),
	relation: z.enum(BOOK_MAP_TRANSITION_RELATION_VALUES),
	rationale: z.string().min(1),
	provenance: z.enum(BOOK_GRAPH_PROVENANCE_VALUES),
	sourceRefs: z.array(graphSourceRefSchema).min(1),
});

const bookMapSchema = z.object({
	archetype: z.enum(BOOK_MAP_ARCHETYPE_VALUES),
	coreQuestion: bookMapStatementSchema,
	thesis: bookMapStatementSchema,
	conclusion: bookMapStatementSchema,
	parts: z.array(bookMapPartSchema).min(2),
	transitions: z.array(bookMapTransitionSchema).min(1),
});

const bookGraphSchema: ZodType<BookGraphEntryData> = z
	.object({
		book: reference("books"),
		title: z.string().min(1),
		stage: z.enum(BOOK_GRAPH_STAGE_VALUES),
		basis: z.array(z.enum(BOOK_GRAPH_BASIS_VALUES)).min(1),
		aiAssisted: z.boolean(),
		layout: z.enum(BOOK_GRAPH_LAYOUT_VALUES).default("cose"),
		summary: z.string().min(1),
		bookMap: bookMapSchema.optional(),
		nodes: z.array(graphNodeSchema).min(1),
		edges: z.array(graphEdgeSchema).min(1),
	})
	.superRefine((graph, context) => {
		const validateEvidence = (
			item: {
				provenance: BookGraphProvenance;
				sourceRefs?: BookGraphSourceRef[];
			},
			path: (string | number)[],
		) => {
			for (const [sourceIndex, source] of (item.sourceRefs ?? []).entries()) {
				if (!graph.basis.includes(source.basis)) {
					context.addIssue({
						code: "custom",
						message: `source basis "${source.basis}" is not declared by the graph`,
						path: [...path, "sourceRefs", sourceIndex, "basis"],
					});
				}
			}

			const sourceBases = item.sourceRefs?.map((source) => source.basis) ?? [];
			if (
				item.provenance === "source_summary" &&
				!sourceBases.some((basis) => basis === "epub" || basis === "notes")
			) {
				context.addIssue({
					code: "custom",
					message: "a source summary must reference EPUB text or notes",
					path: [...path, "sourceRefs"],
				});
			}
			if (
				item.provenance === "personal_note" &&
				!sourceBases.includes("notes")
			) {
				context.addIssue({
					code: "custom",
					message: "a personal note must reference notes",
					path: [...path, "sourceRefs"],
				});
			}
		};

		const nodeIds = new Set<string>();
		for (const [index, node] of graph.nodes.entries()) {
			if (nodeIds.has(node.id)) {
				context.addIssue({
					code: "custom",
					message: `duplicate node id: ${node.id}`,
					path: ["nodes", index, "id"],
				});
			}
			nodeIds.add(node.id);
			validateEvidence(node, ["nodes", index]);
		}

		const edgeIds = new Set<string>();
		for (const [index, edge] of graph.edges.entries()) {
			if (edgeIds.has(edge.id)) {
				context.addIssue({
					code: "custom",
					message: `duplicate edge id: ${edge.id}`,
					path: ["edges", index, "id"],
				});
			}
			edgeIds.add(edge.id);

			if (!nodeIds.has(edge.source)) {
				context.addIssue({
					code: "custom",
					message: `edge source does not exist: ${edge.source}`,
					path: ["edges", index, "source"],
				});
			}
			if (!nodeIds.has(edge.target)) {
				context.addIssue({
					code: "custom",
					message: `edge target does not exist: ${edge.target}`,
					path: ["edges", index, "target"],
				});
			}
			if (edge.source === edge.target) {
				context.addIssue({
					code: "custom",
					message: "self-referencing edges are not supported",
					path: ["edges", index],
				});
			}
			validateEvidence(edge, ["edges", index]);
		}

		if (!graph.nodes.some((node) => node.kind === "core")) {
			context.addIssue({
				code: "custom",
				message: "a book graph must contain at least one core node",
				path: ["nodes"],
			});
		}

		if (graph.bookMap) {
			validateEvidence(graph.bookMap.coreQuestion, ["bookMap", "coreQuestion"]);
			validateEvidence(graph.bookMap.thesis, ["bookMap", "thesis"]);
			validateEvidence(graph.bookMap.conclusion, ["bookMap", "conclusion"]);

			const partIds = new Set<string>();
			const partOrders = new Set<number>();
			const argumentCardIds = new Set<string>();
			const partById = new Map<string, (typeof graph.bookMap.parts)[number]>();
			for (const [index, part] of graph.bookMap.parts.entries()) {
				if (partIds.has(part.id)) {
					context.addIssue({
						code: "custom",
						message: `duplicate book map part id: ${part.id}`,
						path: ["bookMap", "parts", index, "id"],
					});
				}
				partIds.add(part.id);
				partById.set(part.id, part);

				if (partOrders.has(part.order)) {
					context.addIssue({
						code: "custom",
						message: `duplicate book map part order: ${part.order}`,
						path: ["bookMap", "parts", index, "order"],
					});
				}
				partOrders.add(part.order);

				for (const [nodeIndex, nodeId] of part.conceptNodeIds.entries()) {
					if (!nodeIds.has(nodeId)) {
						context.addIssue({
							code: "custom",
							message: `book map concept node does not exist: ${nodeId}`,
							path: ["bookMap", "parts", index, "conceptNodeIds", nodeIndex],
						});
					}
				}

				if (part.maturity === "outline" && part.argumentCards.length > 0) {
					context.addIssue({
						code: "custom",
						message: "an outline book map part cannot contain argument cards",
						path: ["bookMap", "parts", index, "argumentCards"],
					});
				}
				for (const [cardIndex, card] of part.argumentCards.entries()) {
					if (argumentCardIds.has(card.id)) {
						context.addIssue({
							code: "custom",
							message: `duplicate book argument card id: ${card.id}`,
							path: [
								"bookMap",
								"parts",
								index,
								"argumentCards",
								cardIndex,
								"id",
							],
						});
					}
					argumentCardIds.add(card.id);

					for (const [cardNodeIndex, nodeId] of card.conceptNodeIds.entries()) {
						if (!nodeIds.has(nodeId)) {
							context.addIssue({
								code: "custom",
								message: `book argument card concept node does not exist: ${nodeId}`,
								path: [
									"bookMap",
									"parts",
									index,
									"argumentCards",
									cardIndex,
									"conceptNodeIds",
									cardNodeIndex,
								],
							});
						}
					}
					validateEvidence(card, [
						"bookMap",
						"parts",
						index,
						"argumentCards",
						cardIndex,
					]);
				}
				validateEvidence(part, ["bookMap", "parts", index]);
			}

			const transitionIds = new Set<string>();
			const reachablePartIds = new Set<string>();
			const orderedParts = [...graph.bookMap.parts].sort(
				(a, b) => a.order - b.order,
			);
			const firstPart = orderedParts[0];
			if (firstPart) reachablePartIds.add(firstPart.id);

			for (const [index, transition] of graph.bookMap.transitions.entries()) {
				if (transitionIds.has(transition.id)) {
					context.addIssue({
						code: "custom",
						message: `duplicate book map transition id: ${transition.id}`,
						path: ["bookMap", "transitions", index, "id"],
					});
				}
				transitionIds.add(transition.id);

				if (!partIds.has(transition.source)) {
					context.addIssue({
						code: "custom",
						message: `book map transition source does not exist: ${transition.source}`,
						path: ["bookMap", "transitions", index, "source"],
					});
				}
				if (!partIds.has(transition.target)) {
					context.addIssue({
						code: "custom",
						message: `book map transition target does not exist: ${transition.target}`,
						path: ["bookMap", "transitions", index, "target"],
					});
				}
				if (transition.source === transition.target) {
					context.addIssue({
						code: "custom",
						message: "self-referencing book map transitions are not supported",
						path: ["bookMap", "transitions", index],
					});
				}
				const sourcePart = partById.get(transition.source);
				const targetPart = partById.get(transition.target);
				if (sourcePart && targetPart && sourcePart.order >= targetPart.order) {
					context.addIssue({
						code: "custom",
						message: "book map transitions must move forward in part order",
						path: ["bookMap", "transitions", index],
					});
				}
				validateEvidence(transition, ["bookMap", "transitions", index]);
			}

			for (const part of orderedParts) {
				if (!reachablePartIds.has(part.id)) continue;
				for (const transition of graph.bookMap.transitions) {
					if (transition.source === part.id) {
						reachablePartIds.add(transition.target);
					}
				}
			}
			for (const [index, part] of graph.bookMap.parts.entries()) {
				if (!reachablePartIds.has(part.id)) {
					context.addIssue({
						code: "custom",
						message: `book map part is not reachable from the first part: ${part.id}`,
						path: ["bookMap", "parts", index, "id"],
					});
				}
			}
		}

		if (
			graph.stage === "preview" &&
			graph.basis.length === 1 &&
			graph.basis[0] === "notes"
		) {
			context.addIssue({
				code: "custom",
				message: "a preview graph cannot be based on notes only",
				path: ["basis"],
			});
		}

		if (graph.stage === "reviewed" && !graph.basis.includes("notes")) {
			context.addIssue({
				code: "custom",
				message: "a reviewed graph must include personal notes as a basis",
				path: ["basis"],
			});
		}
	});

const bookGraphsCollection: ContentCollection<BookGraphEntryData> =
	defineCollection({
		loader: glob({
			pattern: "**/graph.json",
			base: "./src/content/books",
			generateId: ({ entry }) => bookGraphIdFromEntry(entry),
		}),
		schema: bookGraphSchema,
	});

export const collections: {
	bookGraphs: typeof bookGraphsCollection;
	books: typeof booksCollection;
	dynamic: typeof dynamicCollection;
	posts: typeof postsCollection;
	spec: typeof specCollection;
} = {
	bookGraphs: bookGraphsCollection,
	books: booksCollection,
	dynamic: dynamicCollection,
	posts: postsCollection,
	spec: specCollection,
};
