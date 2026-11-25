export function replaceBookUrl(url: URL): void {
	// Swup restores history.state.url, not necessarily the address bar URL.
	const state = history.state;
	const path = url.pathname + url.search + url.hash;
	history.replaceState(
		state?.source === "swup" ? { ...state, url: path } : state,
		"",
		path,
	);
	// Keep ordinary navbar/directory links distinct from Swup's current page.
	const current = window.swup?.location;
	if (current?.pathname === url.pathname) current.search = url.search;
}
