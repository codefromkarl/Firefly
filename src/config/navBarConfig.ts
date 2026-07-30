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
		icon: "material-symbols:home",
	},
	Archive: {
		name: "归档",
		url: "/archive/",
		icon: "material-symbols:archive",
	},
	Categories: {
		name: "分类",
		url: "/categories/",
		icon: "material-symbols:folder-open-rounded",
	},
	Tags: {
		name: "标签",
		url: "/tags/",
		icon: "material-symbols:tag-rounded",
	},
	Books: {
		name: "书单",
		url: "/books/",
		icon: "material-symbols:menu-book-rounded",
	},
	Lab: {
		name: "实验室",
		url: "/lab/",
		icon: "material-symbols:experiment",
	},
	TechStack: {
		name: "技术栈",
		url: "/tech-stack/",
		icon: "material-symbols:code",
	},
	About: {
		name: "关于我",
		url: "/about/",
		icon: "material-symbols:person",
	},
};

export const navBarConfig: NavBarConfig = {
	links: [
		LinkPresets.Home,
		{
			name: "文章",
			url: "#",
			icon: "material-symbols:article",
			children: [LinkPresets.Archive, LinkPresets.Categories, LinkPresets.Tags],
		},
		{
			name: "探索",
			url: "#",
			icon: "material-symbols:explore",
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
			icon: "fa7-brands:github",
		},
	],
};

export const navBarSearchConfig: NavBarSearchConfig = {
	method: NavBarSearchMethod.PageFind,
};
