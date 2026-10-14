/// <reference types="node" />

export interface CompressionResult {
  data: Buffer;
  encoding: string | null;
}

export function isCompressible(contentType: string, length: number, minSize?: number): boolean;
export function chooseEncoding(acceptEncoding?: string): string | null;

export class ResponseCompressor {
  minSize: number;

  constructor(minSize?: number);

  compress(
    content: Buffer | string,
    contentType: string,
    acceptEncoding?: string
  ): CompressionResult;
}
