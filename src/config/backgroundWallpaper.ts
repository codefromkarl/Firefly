import type { BackgroundWallpaperConfig } from "@/types/backgroundWallpaper";

export const backgroundWallpaper: BackgroundWallpaperConfig = {
	mode: "banner",
	playerEnable: false,
	src: {
		desktop: "/images/home-bg.webp",
		mobile: "/images/home-bg.webp",
	},
	common: {
		dimOpacity: 0.3,
		homeText: {
			enable: true,
			title: "CodeFromKarl",
			titleSize: "4rem",
			subtitle: "极简分享，真诚成长",
			subtitleSize: "1.4rem",
			typewriter: {
				enable: false,
				speed: 100,
				deleteSpeed: 50,
				pauseTime: 2000,
			},
		},
		postInfo: {
			mode: "description",
		},
		navbar: {
			transparentMode: "semi",
			enableBlur: true,
			blur: 5,
		},
		waves: {
			enable: {
				desktop: false,
				mobile: false,
			},
		},
		gradient: {
			enable: {
				desktop: true,
				mobile: true,
			},
			height: "20%",
		},
		carousel: {
			enable: false,
		},
	},
	banner: {
		position: "center",
	},
};
