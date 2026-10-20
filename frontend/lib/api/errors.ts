/**
 * @file lib/api/errors.ts
 * @brief Backend error envelope: { error: { code, message, details? } }.
 *        ApiError preserves status + envelope for UI mapping.
 */

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  static fromUnknown(status: number, body: unknown): ApiError {
    if (body && typeof body === "object" && "error" in body) {
      const env = (body as ErrorEnvelope).error;
      if (env && typeof env.message === "string") {
        return new ApiError(
          status,
          env.code ?? "unknown",
          env.message,
          env.details,
        );
      }
    }
    return new ApiError(status, "unknown", `Request failed (${status})`);
  }
}

export function formatApiError(
  err: unknown,
  fallback = "Something went wrong.",
): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}
