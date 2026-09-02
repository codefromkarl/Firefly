import type { LicenseConfig } from "../types/licenseConfig";

export const licenseConfig: LicenseConfig = {
	// 是否启用文章顶部许可证信息显示
	enable: false,

	// 许可证名称及链接
	name: "CC BY-NC-SA 4.0",
	url: "https://creativecommons.org/licenses/by-nc-sa/4.0/",

	// 可选：自定义许可证图标（Lucide 图标名，如 "lucide:copyright"）
	// 留空时根据许可证名称自动匹配，匹配规则如下：
	//   CC BY / CC BY-SA / CC BY-NC / CC BY-NC-SA / CC BY-ND / CC BY-NC-ND 等 CC 系列
	//   → lucide:copyright
	//   CC0 1.0
	//   → lucide:copyright
	//   Public Domain / 公共领域
	//   → lucide:copyright
	//   MIT / Apache / BSD / ISC / MPL / GPL / LGPL / AGPL / MulanPSL / Unlicense
	//   → lucide:shield-check
	//   其余未匹配的许可证（如 All Rights Reserved、WTFPL 等）
	//   → lucide:copyright
	icon: "",
};
