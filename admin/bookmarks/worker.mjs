import client from "./client.js.txt";
import { makeHandler } from "./handler.mjs";
import shell from "./page.html.txt";

export default { fetch: makeHandler({ shell, client }) };
