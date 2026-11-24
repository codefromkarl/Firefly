import banner from "../../src/assets/images/home-bg.webp";
import client from "./client.js.txt";
import { makeHandler } from "./handler.mjs";
import importShell from "./import.html.txt";
import shell from "./page.html.txt";

export default { fetch: makeHandler({ shell, importShell, client, banner }) };
