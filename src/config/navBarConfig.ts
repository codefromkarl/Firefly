import {
	type NavBarConfig,
	type NavBarLink,
	type NavBarSearchConfig,
	NavBarSearchMethod,
} from "../types/navBarConfig";

export const LinkPresets: Record<string, NavBarLink> = {
	Home: {
		name: "主页",
		url: "/",
		icon: "lucide:house",
	},
	Archive: {
		name: "归档",
		url: "/archive/",
		icon: "lucide:archive",
	},
	Categories: {
		name: "分类",
		url: "/categories/",
		icon: "lucide:folder-open",
	},
	Tags: {
		name: "标签",
		url: "/tags/",
		icon: "lucide:tag",
	},
	Books: {
		name: "书单",
		url: "/books/",
		icon: "lucide:library",
	},
	Lab: {
		name: "实验室",
		url: "/lab/",
		icon: "lucide:flask-conical",
	},
	TechStack: {
		name: "技术栈",
		url: "/tech-stack/",
		icon: "lucide:code",
	},
	About: {
		name: "关于我",
		url: "/about/",
		icon: "lucide:user",
	},
};

export const navBarConfig: NavBarConfig = {
	links: [
		LinkPresets.Home,
		{
			name: "文章",
			url: "#",
			icon: "lucide:file-text",
			children: [LinkPresets.Archive, LinkPresets.Categories, LinkPresets.Tags],
		},
		{
			name: "探索",
			url: "#",
			icon: "lucide:compass",
			children: [
				LinkPresets.Books,
				LinkPresets.Lab,
				LinkPresets.TechStack,
				LinkPresets.About,
			],
		},
		{
			name: "GitHub",
			url: "https://github.com/codefromkarl",
			external: true,
			icon: "lucide:github",
		},
	],
};

export const navBarSearchConfig: NavBarSearchConfig = {
	method: NavBarSearchMethod.PageFind,
};
