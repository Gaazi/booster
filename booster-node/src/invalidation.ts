/** Exchange cache invalidation notices between worker processes. */
import { appendFileSync, closeSync, existsSync, mkdirSync, openSync, readSync, statSync, truncateSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

export const FULL_CLEAR = "*";

/** Publish and observe invalidation notices. */
export interface InvalidationBus {
  publish(prefix: string): void;
  drain(): string[];
}

/** Keep invalidation inside the current process. */
export class LocalInvalidationBus implements InvalidationBus {
  /** Ignore the notice because no other worker exists. */
  public publish(prefix: string): void { /* process-local engine */ }
  /** Return no notices. */
  public drain(): string[] { return []; }
}

/** Exchange notices through one shared file, for workers on the same host. */
export class FileInvalidationBus implements InvalidationBus {
  private readonly path: string;
  private readonly maxBytes: number;
  private readonly handle: number;
  private position = 0;

  /** Open the shared notice file for reading and later appending. */
  constructor(path: string, maxBytes = 1_000_000) {
    this.path = path;
    this.maxBytes = maxBytes;
    mkdirSync(dirname(path), { recursive: true });
    if (!existsSync(path)) writeFileSync(path, "");
    this.handle = openSync(path, "r");
  }

  /** Append one notice for the other workers. */
  public publish(prefix: string): void {
    appendFileSync(this.path, prefix + "\n");
    if (statSync(this.path).size > this.maxBytes) truncateSync(this.path, 0);
  }

  /** Read the notices written since the last drain. */
  public drain(): string[] {
    const size = statSync(this.path).size;
    if (this.position > size) { this.position = 0; return [FULL_CLEAR]; }
    const length = size - this.position;
    if (length <= 0) return [];
    const buffer = Buffer.alloc(length);
    const read = readSync(this.handle, buffer, 0, length, this.position);
    this.position += read;
    return buffer.toString("utf8").split("\n").map(line => line.trim()).filter(Boolean);
  }

  /** Release the notice file handle. */
  public close(): void {
    closeSync(this.handle);
  }
}
