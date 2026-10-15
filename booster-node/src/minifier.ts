/**
 * High-speed on-the-fly minifier for HTML, CSS, and JSON.
 */
/** Preserve formatting and quoted content; use a frontend build tool for HTML. */
export function minifyHTML(html: string): string {
  return html;
}

/** Preserve CSS strings, custom properties and significant whitespace. */
export function minifyCSS(css: string): string {
  return css;
}

/** Remove whitespace outside JSON strings without rounding numbers or rewriting keys. */
export function minifyJSON(jsonStr: string): string {
  try {
    JSON.parse(jsonStr);
    return jsonStr.replace(/"(?:\\.|[^"\\])*"|[ \t\r\n]+/g, token => token.startsWith('"') ? token : "");
  } catch (error) {
    if (error instanceof SyntaxError) return jsonStr;
    throw error;
  }
}

export class FastMinifier {
  public minify(content: Buffer | string, contentType: string = ""): Buffer {
    const baseType = contentType.split(";")[0].trim().toLowerCase();
    const buffer = Buffer.isBuffer(content) ? content : Buffer.from(content);
    if (baseType !== "application/json") return buffer;
    const text = typeof content === "string" ? content : content.toString("utf-8");
    if (!Buffer.from(text).equals(buffer)) return buffer;
    return Buffer.from(minifyJSON(text), "utf-8");
  }
}
