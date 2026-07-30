import type { PagefindApi } from "@/types/pagefind";
import { url } from "@/utils/url-utils";

let pagefindLoadPromise: Promise<PagefindApi> | undefined;

export function loadPagefind(): Promise<PagefindApi> {
	if (window.pagefind) return Promise.resolve(window.pagefind);
	if (pagefindLoadPromise) return pagefindLoadPromise;

	const scriptUrl = url("/pagefind/pagefind.js");
	pagefindLoadPromise = import(/* @vite-ignore */ scriptUrl)
		.then(async (module) => {
			const pagefind = module as PagefindApi;
			await pagefind.options({ excerptLength: 20 });
			window.pagefind = pagefind;
			document.dispatchEvent(new Event("pagefindready"));
			return pagefind;
		})
		.catch((error: unknown) => {
			pagefindLoadPromise = undefined;
			document.dispatchEvent(new Event("pagefindloaderror"));
			throw error;
		});

	return pagefindLoadPromise;
}
