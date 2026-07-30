import { siteConfig } from "../config/siteConfig";
import type I18nKey from "./i18nKey";

export type Translation = {
	[K in I18nKey]: string;
};

type TranslationModule = Record<string, Translation>;
type TranslationFile = "en" | "ja" | "ko" | "ru" | "zh_CN" | "zh_TW";

const LANGUAGE_FILES: Record<string, TranslationFile> = {
	en: "en",
	en_us: "en",
	en_gb: "en",
	en_au: "en",
	zh_cn: "zh_CN",
	zh_tw: "zh_TW",
	ja: "ja",
	ja_jp: "ja",
	ru: "ru",
	ru_ru: "ru",
	ko: "ko",
	ko_kr: "ko",
};

const translationModules = import.meta.glob<TranslationModule>(
	"./languages/*.ts",
);

async function loadTranslation(file: TranslationFile): Promise<Translation> {
	const loader = translationModules[`./languages/${file}.ts`];
	if (!loader) throw new Error(`Translation module not found: ${file}`);

	const module = await loader();
	const translation = module[file];
	if (!translation) throw new Error(`Translation export not found: ${file}`);
	return translation;
}

const configuredLanguage = siteConfig.lang.toLowerCase();
const currentLanguageFile = LANGUAGE_FILES[configuredLanguage] ?? "en";
const currentTranslation = await loadTranslation(currentLanguageFile);
const chineseTranslation =
	currentLanguageFile === "zh_CN"
		? currentTranslation
		: await loadTranslation("zh_CN");
const defaultTranslation =
	currentLanguageFile === "en"
		? currentTranslation
		: await loadTranslation("en");

export function i18n(key: I18nKey): string {
	const value = currentTranslation[key];

	// 如果当前语言没有翻译（或为空），则使用中文作为备选
	if (!value && currentLanguageFile !== "zh_CN") {
		const chineseValue = chineseTranslation[key];
		if (chineseValue) {
			return chineseValue;
		}
	}

	return value || defaultTranslation[key];
}
