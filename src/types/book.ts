export const BOOK_STATUS_VALUES = ["wishlist", "reading", "read"] as const;
export type BookStatus = (typeof BOOK_STATUS_VALUES)[number];

export const BOOK_SHELF_VALUES = [
	"cognition-and-decisions",
	"wealth-and-growth",
	"psychology-and-relationships",
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

export interface BookMapPart {
	id: string;
	order: number;
	title: string;
	role: BookMapPartRole;
	question: string;
	thesis: string;
	inputUnderstanding: string;
	outputUnderstanding: string;
	conceptNodeIds: string[];
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

export interface BookCardData {
	id: string;
	title: string;
	originalTitle?: string;
	authors: string[];
	description: string;
	previewFocus: string;
	status: BookStatus;
	shelf: BookShelf;
	topics: string[];
	coverUrl: string;
	url: string;
	graphStage: BookGraphStage;
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
