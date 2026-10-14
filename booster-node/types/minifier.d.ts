/// <reference types="node" />

export function minifyHTML(html: string): string;
export function minifyCSS(css: string): string;
export function minifyJSON(jsonStr: string): string;

export class FastMinifier {
  minify(content: Buffer | string, contentType?: string): Buffer;
}
