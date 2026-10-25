/** Exchange cache invalidation notices between worker processes. */
import {appendFileSync, closeSync, existsSync, mkdirSync, openSync, readSync, statSync, writeFileSync} from "node:fs";
import {dirname, resolve} from "node:path";
import {randomUUID} from "node:crypto";
import {withFileBusLock} from "./file-bus-lock.ts";

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
  private readonly lock: string;
  private epoch: string;
  private position: number;

  /** Open the shared notice file for reading and later appending. */
  constructor(path: string, maxBytes = 1_000_000) {
    if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) throw new Error("maxBytes must be a positive integer");
    this.path = resolve(path);
    this.maxBytes = maxBytes;
    this.lock = this.path + ".lock";
    mkdirSync(dirname(this.path), {recursive: true});
    this.epoch = withFileBusLock(this.lock, () => this.header());
    this.position = Buffer.byteLength(this.epoch);
  }

  /** Initialize or migrate the generation header shared with Python. */
  private header(): string {
    if (existsSync(this.path)) {
      const handle = openSync(this.path, "r");
      const buffer = Buffer.alloc(34);
      try {
        const read = readSync(handle, buffer, 0, 34, 0);
        const header = buffer.toString("ascii", 0, read);
        if (/^#[a-f0-9]{32}\n$/.test(header)) return header;
      } finally { closeSync(handle); }
    }
    const header = "#" + randomUUID().replaceAll("-", "") + "\n";
    writeFileSync(this.path, header);
    return header;
  }

  /** Append one notice for the other workers. */
  public publish(prefix: string): void {
    const record = JSON.stringify(prefix) + "\n";
    withFileBusLock(this.lock, () => {
      this.header();
      if (statSync(this.path).size + Buffer.byteLength(record) > this.maxBytes) {
        writeFileSync(this.path, "#" + randomUUID().replaceAll("-", "") + "\n");
      } else appendFileSync(this.path, record);
    });
  }

  /** Read the notices written since the last drain. */
  public drain(): string[] {
    return withFileBusLock(this.lock, () => {
      const epoch = this.header(), size = statSync(this.path).size;
      if (epoch !== this.epoch || this.position > size) {
        this.epoch = epoch; this.position = size;
        return [FULL_CLEAR];
      }
      const buffer = Buffer.alloc(size - this.position);
      const handle = openSync(this.path, "r");
      try {
        const read = readSync(handle, buffer, 0, buffer.length, this.position);
        this.position += read;
        return buffer.toString("utf8", 0, read).split("\n").filter(Boolean).map(line => JSON.parse(line) as string);
      } finally { closeSync(handle); }
    });
  }

  /** Retain the lifecycle API; each operation now closes its own file handle. */
  public close(): void { /* no persistent handle */ }
}
