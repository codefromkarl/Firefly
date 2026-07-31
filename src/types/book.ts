export const BOOK_STATUS_VALUES = ["wishlist", "reading", "read"] as const;
export type BookStatus = (typeof BOOK_STATUS_VALUES)[number];

export const BOOK_SHELF_VALUES = [
	"cognition-and-decisions",
	"wealth-and-growth",
	"psychology-and-relationships",
	"literature-and-life",
] as const;
export type BookShelf = (typeof BOOK_SHELF_VALUES)[number];

export const BOOK_GRAPH_STAGE_VALUES = [
	"preview",
	"reading",
	"reviewed",
] as const;
export type BookGraphStage = (typeof BOOK_GRAPH_STAGE_VALUES)[number];

export const BOOK_GRAPH_BASIS_VALUES = [
	"metadata",
	"toc",
	"epub",
	"notes",
] as const;
export type BookGraphBasis = (typeof BOOK_GRAPH_BASIS_VALUES)[number];

export const BOOK_GRAPH_PROVENANCE_VALUES = [
	"source_summary",
	"editorial_inference",
	"personal_note",
] as const;
export type BookGraphProvenance = (typeof BOOK_GRAPH_PROVENANCE_VALUES)[number];

export const BOOK_GRAPH_LAYOUT_VALUES = [
	"cose",
	"breadthfirst",
	"circle",
] as const;
export type BookGraphLayout = (typeof BOOK_GRAPH_LAYOUT_VALUES)[number];

export const BOOK_GRAPH_NODE_KIND_VALUES = [
	"core",
	"concept",
	"model",
	"bias",
	"practice",
	"outcome",
	"chapter",
] as const;
export type BookGraphNodeKind = (typeof BOOK_GRAPH_NODE_KIND_VALUES)[number];

export const BOOK_GRAPH_RELATION_VALUES = [
	"part_of",
	"explains",
	"contrasts",
	"causes",
	"supports",
	"applies_to",
	"leads_to",
] as const;
export type BookGraphRelation = (typeof BOOK_GRAPH_RELATION_VALUES)[number];

export const BOOK_MAP_ARCHETYPE_VALUES = [
	"argumentative_monograph",
	"progressive_dialogue",
	"essay_collection",
	"curated_anthology",
	"narrative",
] as const;
export type BookMapArchetype = (typeof BOOK_MAP_ARCHETYPE_VALUES)[number];

export const BOOK_MAP_PART_ROLE_VALUES = [
	"pose_problem",
	"define",
	"diagnose",
	"explain_mechanism",
	"provide_evidence",
	"challenge",
	"synthesize",
	"prescribe",
	"conclude",
] as const;
export type BookMapPartRole = (typeof BOOK_MAP_PART_ROLE_VALUES)[number];

export const BOOK_MAP_TRANSITION_RELATION_VALUES = [
	"motivates",
	"defines",
	"explains",
	"challenges",
	"resolves",
	"enables",
	"concludes",
] as const;
export type BookMapTransitionRelation =
	(typeof BOOK_MAP_TRANSITION_RELATION_VALUES)[number];

export const BOOK_MAP_PART_MATURITY_VALUES = [
	"outline",
	"developing",
	"developed",
] as const;
export type BookMapPartMaturity =
	(typeof BOOK_MAP_PART_MATURITY_VALUES)[number];

export const BOOK_ARGUMENT_CARD_KIND_VALUES = [
	"mechanism",
	"evidence",
	"manifestation",
	"practice",
	"boundary",
] as const;
export type BookArgumentCardKind =
	(typeof BOOK_ARGUMENT_CARD_KIND_VALUES)[number];

export const BOOK_ARGUMENT_CONTEXT_VALUES = [
	"book_argument",
	"external_research",
	"cross_book",
	"personal_reflection",
] as const;
export type BookArgumentContext = (typeof BOOK_ARGUMENT_CONTEXT_VALUES)[number];

export interface BookGraphSourceRef {
	basis: BookGraphBasis;
	locator: string;
	quote?: string;
}

export interface BookMapStatement {
	text: string;
	provenance: BookGraphProvenance;
	sourceRefs: BookGraphSourceRef[];
}

export interface BookArgumentCard {
	id: string;
	kind: BookArgumentCardKind;
	title: string;
	summary: string;
	context: BookArgumentContext;
	conceptNodeIds: string[];
	provenance: BookGraphProvenance;
	sourceRefs: BookGraphSourceRef[];
}

export interface BookMapPart {
	id: string;
	order: number;
	title: string;
	role: BookMapPartRole;
	maturity: BookMapPartMaturity;
	question: string;
	thesis: string;
	inputUnderstanding: string;
	outputUnderstanding: string;
	conceptNodeIds: string[];
	argumentCards: BookArgumentCard[];
	provenance: BookGraphProvenance;
	sourceRefs: BookGraphSourceRef[];
}

export interface BookMapTransition {
	id: string;
	source: string;
	target: string;
	relation: BookMapTransitionRelation;
	rationale: string;
	provenance: BookGraphProvenance;
	sourceRefs: BookGraphSourceRef[];
}

export interface BookMapData {
	archetype: BookMapArchetype;
	coreQuestion: BookMapStatement;
	thesis: BookMapStatement;
	conclusion: BookMapStatement;
	parts: BookMapPart[];
	transitions: BookMapTransition[];
}

export interface BookGraphNode {
	id: string;
	label: string;
	kind: BookGraphNodeKind;
	summary: string;
	provenance: BookGraphProvenance;
	sourceRefs: BookGraphSourceRef[];
	chapter?: string;
	anchor?: string;
	importance: 1 | 2 | 3;
}

export interface BookGraphEdge {
	id: string;
	source: string;
	target: string;
	relation: BookGraphRelation;
	directed: boolean;
	summary?: string;
	provenance: BookGraphProvenance;
	sourceRefs?: BookGraphSourceRef[];
}

export interface BookGraphData {
	title: string;
	stage: BookGraphStage;
	basis: BookGraphBasis[];
	aiAssisted: boolean;
	layout: BookGraphLayout;
	summary: string;
	bookMap?: BookMapData;
	nodes: BookGraphNode[];
	edges: BookGraphEdge[];
}

export interface BookExcerpt {
	text: string;
	source: string;
	url?: string;
}

export interface BookSourceCitation {
	text: string;
	source: string;
	url: string;
}

export const BOOK_READING_REASON_KIND_VALUES = [
	"insight",
	"scope",
	"perspective",
	"readability",
	"application",
	"boundary",
] as const;
export type BookReadingReasonKind =
	(typeof BOOK_READING_REASON_KIND_VALUES)[number];

export interface BookReadingReason extends BookSourceCitation {
	title: string;
	kind: BookReadingReasonKind;
}

export interface BookCardData {
	id: string;
	title: string;
	originalTitle?: string;
	authors: string[];
	description: string;
	sourceIntroduction: string;
	status: BookStatus;
	shelf: BookShelf;
	topics: string[];
	coverUrl: string;
	url: string;
}

export interface BookDirectoryItem {
	id: string;
	title: string;
	shelf: BookShelf;
	url: string;
}

export const BOOK_STATUS_LABELS: Record<BookStatus, string> = {
	wishlist: "想读",
	reading: "在读",
	read: "读过",
};

export const BOOK_SHELF_LABELS: Record<BookShelf, string> = {
	"cognition-and-decisions": "认知与决策",
	"wealth-and-growth": "财富与成长",
	"psychology-and-relationships": "心理与关系",
	"literature-and-life": "文学与人生",
};

export const BOOK_GRAPH_STAGE_LABELS: Record<BookGraphStage, string> = {
	preview: "预读知识地图",
	reading: "阅读中知识地图",
	reviewed: "正式知识图谱",
};

export const BOOK_GRAPH_BASIS_LABELS: Record<BookGraphBasis, string> = {
	metadata: "书籍元数据",
	toc: "目录",
	epub: "EPUB 正文",
	notes: "个人读书笔记",
};

export const BOOK_GRAPH_PROVENANCE_LABELS: Record<BookGraphProvenance, string> =
	{
		source_summary: "来源内容的重新表述",
		editorial_inference: "AI / 编辑整理推断",
		personal_note: "个人读书笔记",
	};

export const BOOK_GRAPH_NODE_KIND_LABELS: Record<BookGraphNodeKind, string> = {
	core: "核心主题",
	concept: "概念",
	model: "模型",
	bias: "偏差",
	practice: "实践",
	outcome: "结果",
	chapter: "章节",
};

export const BOOK_GRAPH_RELATION_LABELS: Record<BookGraphRelation, string> = {
	part_of: "属于",
	explains: "解释",
	contrasts: "对照",
	causes: "导致",
	supports: "支持",
	applies_to: "应用于",
	leads_to: "通向",
};

export const BOOK_MAP_ARCHETYPE_LABELS: Record<BookMapArchetype, string> = {
	argumentative_monograph: "论证型专著",
	progressive_dialogue: "渐进式对话",
	essay_collection: "主题短论集",
	curated_anthology: "编纂型文集",
	narrative: "叙事作品",
};

export const BOOK_MAP_PART_ROLE_LABELS: Record<BookMapPartRole, string> = {
	pose_problem: "提出问题",
	define: "界定概念",
	diagnose: "诊断问题",
	explain_mechanism: "解释机制",
	provide_evidence: "提供证据",
	challenge: "提出挑战",
	synthesize: "综合观点",
	prescribe: "给出实践",
	conclude: "形成结论",
};

export const BOOK_MAP_PART_MATURITY_LABELS: Record<
	BookMapPartMaturity,
	string
> = {
	outline: "待补充",
	developing: "整理中",
	developed: "已展开",
};

export const BOOK_ARGUMENT_CARD_KIND_LABELS: Record<
	BookArgumentCardKind,
	string
> = {
	mechanism: "机 · 解释机制",
	evidence: "证 · 依据线索",
	manifestation: "症 · 现实表现",
	practice: "法 · 实践方法",
	boundary: "界 · 适用边界",
};

export const BOOK_ARGUMENT_CONTEXT_LABELS: Record<BookArgumentContext, string> =
	{
		book_argument: "本书论证",
		external_research: "外部研究线索",
		cross_book: "跨书关联",
		personal_reflection: "个人思考",
	};

export const BOOK_MAP_TRANSITION_RELATION_LABELS: Record<
	BookMapTransitionRelation,
	string
> = {
	motivates: "引出",
	defines: "界定",
	explains: "解释",
	challenges: "质疑",
	resolves: "回应",
	enables: "奠定",
	concludes: "归结",
};
