/** Fixed reason names for responses that were not stored in the shared cache. */
export const REASONS = {
  METHOD: "method_not_read",
  POLICY: "route_not_selected",
  CREDENTIALS: "credentialed_request",
  PERSONALIZED: "personalized_scope",
  REQUEST_DIRECTIVE: "request_directive",
  RESPONSE_DIRECTIVE: "response_not_public",
  STATUS: "status_not_cacheable",
  ENCODED: "already_encoded",
  STREAMED: "streamed_response",
  TOO_LARGE: "body_too_large",
  STORED: "stored",
} as const;

/** Count why a response was not stored, without recording any request data. */
export class BypassTracker {
  private readonly counts = new Map<string, number>();

  /** Count one decision for a served response. */
  public record(reason: string): void {
    this.counts.set(reason, (this.counts.get(reason) || 0) + 1);
  }

  /** Return the reason counters as a stable sorted mapping. */
  public getCounts(): Record<string, number> {
    return Object.fromEntries([...this.counts.entries()].sort(([a], [b]) => a.localeCompare(b)));
  }

  /** Clear every counter. */
  public reset(): void {
    this.counts.clear();
  }
}
