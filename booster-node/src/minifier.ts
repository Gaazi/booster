/**
 * High-speed on-the-fly minifier for HTML, CSS, and JSON.
 */
const RE_HTML_COMMENTS = /<!--(?!\[if).*?-->/gs;
const RE_HTML_SPACES = />\s+</g;
const RE_CSS_COMMENTS = /\/\*.*?\*\//gs;
const RE_CSS_SPACES = /\s*([\{\}:;,>])\s*/g;

export function minifyHTML(html: string): string {
  return html.replace(RE_HTML_COMMENTS, "").replace(RE_HTML_SPACES, "><").trim();
}

export function minifyCSS(css: string): string {
  return css.replace(RE_CSS_COMMENTS, "").replace(RE_CSS_SPACES, "$1").trim();
}

export function minifyJSON(jsonStr: string): string {
  try {
    return JSON.stringify(JSON.parse(jsonStr));
  } catch {
    return jsonStr;
  }
}

export class FastMinifier {
  public minify(content: Buffer | string, contentType: string = ""): Buffer {
    const baseType = contentType.split(";")[0].trim().toLowerCase();
    const text = typeof content === "string" ? content : content.toString("utf-8");

    if (baseType === "text/html") {
      return Buffer.from(minifyHTML(text), "utf-8");
    }
    if (baseType === "text/css") {
      return Buffer.from(minifyCSS(text), "utf-8");
    }
    if (baseType === "application/json") {
      return Buffer.from(minifyJSON(text), "utf-8");
    }

    return Buffer.isBuffer(content) ? content : Buffer.from(content);
  }
}
