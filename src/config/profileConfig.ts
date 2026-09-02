import type { ProfileConfig } from "../types/profileConfig";

export const profileConfig: ProfileConfig = {
	avatar: "/images/avatar.png",
	name: "Karl",
	bio: "AI Agent 开发者，记录技术实践与成长",
	links: [
		{
			name: "GitHub",
			icon: "lucide:github",
			url: "https://github.com/codefromkarl",
			showName: false,
		},
		{
			name: "Email",
			icon: "lucide:mail",
			url: "mailto:1069123094@qq.com",
			showName: false,
		},
		{
			name: "RSS",
			icon: "lucide:rss",
			url: "/rss.xml",
			showName: false,
		},
	],
};
