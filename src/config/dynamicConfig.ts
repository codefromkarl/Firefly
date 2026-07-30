import type { DynamicConfig } from "@/types/dynamicConfig";

export const dynamicConfig: DynamicConfig = {
	title: "",
	description: "",
	profileUrl: "/lab/",
	showComment: false,
	itemsPerPage: 20,
	apiUrl: "/api/dynamic.json",
	memos: {
		enable: false,
		apiUrl: "",
		parent: "",
	},
};
