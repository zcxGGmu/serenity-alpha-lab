import type { ReportArtifact } from '../types';
import { decodeCanonicalReportArtifact } from './canonicalReportArtifact';

const LATEST_ARTIFACT_ENDPOINT =
  '/api/artifacts/stock-analysis/latest';

type ReportArtifactLoadKind = 'unavailable' | 'blocked';

interface ArtifactErrorClassification {
  code: string;
  kind: ReportArtifactLoadKind;
  fallbackReason: string;
  allowedReasons: ReadonlySet<string>;
}

const HTTP_ERROR_CLASSIFICATIONS: Readonly<
  Record<number, ArtifactErrorClassification>
> = {
  404: {
    code: 'artifact_not_found',
    kind: 'unavailable',
    fallbackReason: 'artifact_not_found',
    allowedReasons: new Set([
      'stock_analysis_artifact_missing',
      'stock_analysis_report_missing',
    ]),
  },
  409: {
    code: 'artifact_blocked',
    kind: 'blocked',
    fallbackReason: 'artifact_blocked',
    allowedReasons: new Set([
      'research_only_required',
      'report_gate_research_only_required',
      'report_safety_failed',
      'research_boundary_required',
    ]),
  },
  422: {
    code: 'artifact_invalid',
    kind: 'unavailable',
    fallbackReason: 'artifact_invalid',
    allowedReasons: new Set([
      'artifact_type_missing',
      'artifact_type_unsupported',
      'forbidden_field',
      'generated_at_invalid',
      'key_claim_invalid',
      'key_claim_provenance_missing',
      'key_claims_missing',
      'local_path_detected',
      'manifest_json_invalid',
      'manifest_object_required',
      'manifest_path_invalid',
      'manifest_unreadable',
      'query_invalid',
      'readiness_invalid',
      'readiness_missing',
      'report_gate_invalid',
      'report_gate_missing',
      'report_path_invalid',
      'report_safety_invalid',
      'reports_invalid',
      'reports_missing',
      'schema_version_missing',
      'schema_version_unsupported',
      'skeptical_review_invalid',
      'skeptical_review_missing',
      'source_coverage_invalid',
      'source_coverage_missing',
      'stock_analysis_report_unreadable',
      'stock_name_invalid',
      'symbol_invalid',
    ]),
  },
};

export interface ReportArtifactSource {
  loadLatest(signal?: AbortSignal): Promise<ReportArtifact>;
}

export class ReportArtifactLoadError extends Error {
  constructor(
    readonly kind: ReportArtifactLoadKind,
    readonly reason: string,
  ) {
    super(reason);
    this.name = 'ReportArtifactLoadError';
  }
}

export function createHttpReportArtifactSource(
  fetchImpl: typeof fetch = fetch,
): ReportArtifactSource {
  return {
    async loadLatest(signal?: AbortSignal): Promise<ReportArtifact> {
      let response: Response;
      try {
        response = await fetchImpl(LATEST_ARTIFACT_ENDPOINT, {
          method: 'GET',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal,
        });
      } catch (error) {
        if (isAbortError(error, signal)) {
          throw new ReportArtifactLoadError(
            'unavailable',
            'request_aborted',
          );
        }
        throw new ReportArtifactLoadError(
          'unavailable',
          'network_unavailable',
        );
      }

      const payload = await readJsonOrThrow(response, signal);
      if (!response.ok) {
        throw classifyArtifactError(response.status, payload);
      }

      try {
        return decodeCanonicalReportArtifact(payload);
      } catch {
        throw new ReportArtifactLoadError(
          'unavailable',
          'artifact_payload_invalid',
        );
      }
    },
  };
}

async function readJsonOrThrow(
  response: Response,
  signal?: AbortSignal,
): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    if (isAbortError(error, signal)) {
      throw new ReportArtifactLoadError(
        'unavailable',
        'request_aborted',
      );
    }
    if (!response.ok) {
      throw classifyArtifactError(response.status, undefined);
    }
    if (error instanceof TypeError) {
      throw new ReportArtifactLoadError(
        'unavailable',
        'network_unavailable',
      );
    }
    throw new ReportArtifactLoadError(
      'unavailable',
      'artifact_response_invalid',
    );
  }
}

function classifyArtifactError(
  status: number,
  payload: unknown,
): ReportArtifactLoadError {
  const classification = HTTP_ERROR_CLASSIFICATIONS[status];
  if (!classification) {
    return new ReportArtifactLoadError(
      'unavailable',
      'artifact_unavailable',
    );
  }

  const envelope = isRecord(payload) && isRecord(payload.error)
    ? payload.error
    : undefined;
  const reason =
    envelope?.code === classification.code &&
    typeof envelope.reason === 'string' &&
    classification.allowedReasons.has(envelope.reason)
      ? envelope.reason
      : classification.fallbackReason;

  return new ReportArtifactLoadError(classification.kind, reason);
}

function isAbortError(
  error: unknown,
  signal?: AbortSignal,
): boolean {
  return signal?.aborted === true ||
    (isRecord(error) && error.name === 'AbortError');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
