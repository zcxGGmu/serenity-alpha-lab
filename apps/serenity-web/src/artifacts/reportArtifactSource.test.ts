import { describe, expect, it, vi } from 'vitest';

import {
  canonicalReportArtifactWireFixture,
  reportArtifactFixture,
} from '../test/fixtures/reportArtifacts';
import {
  ReportArtifactLoadError,
  createHttpReportArtifactSource,
} from './reportArtifactSource';

describe('createHttpReportArtifactSource', () => {
  it('requests the relative latest-artifact endpoint and decodes the response', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(canonicalReportArtifactWireFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const source = createHttpReportArtifactSource(fetchImpl);
    const controller = new AbortController();

    const artifact = await source.loadLatest(controller.signal);

    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/artifacts/stock-analysis/latest',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      }),
    );
    expect(artifact).toEqual(reportArtifactFixture);
  });

  it.each([
    [404, 'artifact_not_found', 'unavailable', 'stock_analysis_artifact_missing'],
    [409, 'artifact_blocked', 'blocked', 'report_safety_failed'],
    [422, 'artifact_invalid', 'unavailable', 'key_claim_provenance_missing'],
  ] as const)(
    'classifies HTTP %s without exposing response bodies',
    async (status, code, kind, reason) => {
      const source = createHttpReportArtifactSource(
        vi.fn().mockResolvedValue(
          new Response(
            JSON.stringify({
              error: { code, reason },
              raw: '/Users/example/private.json',
            }),
            { status },
          ),
        ),
      );

      const caught = await captureLoadError(source.loadLatest());

      expect(caught).toMatchObject({ kind, reason });
      expect(String(caught)).not.toContain('/Users/example');
    },
  );

  it.each(ALLOWED_HTTP_ERROR_REASONS)(
    'preserves allowlisted %s reason %s',
    async (status, code, reason) => {
      const source = createHttpReportArtifactSource(
        vi.fn().mockResolvedValue(
          new Response(
            JSON.stringify({
              error: { code, reason },
            }),
            { status },
          ),
        ),
      );

      await expect(source.loadLatest()).rejects.toMatchObject({ reason });
    },
  );

  it.each([
    [404, 'unavailable', 'artifact_not_found'],
    [409, 'blocked', 'artifact_blocked'],
    [422, 'unavailable', 'artifact_invalid'],
  ] as const)(
    'uses a sanitized fallback for malformed HTTP %s envelopes',
    async (status, kind, reason) => {
      const source = createHttpReportArtifactSource(
        vi.fn().mockResolvedValue(
          new Response(
            JSON.stringify({
              error: {
                code: 'unexpected_code',
                reason: '/Users/example/private.json',
              },
            }),
            { status },
          ),
        ),
      );

      await expect(source.loadLatest()).rejects.toMatchObject({ kind, reason });
    },
  );

  it.each([
    [404, 'unavailable', 'artifact_not_found'],
    [409, 'blocked', 'artifact_blocked'],
    [422, 'unavailable', 'artifact_invalid'],
  ] as const)(
    'preserves the HTTP %s classification when the error body is invalid JSON',
    async (status, kind, reason) => {
      const source = createHttpReportArtifactSource(
        vi.fn().mockResolvedValue(
          new Response('{invalid-json', { status }),
        ),
      );

      await expect(source.loadLatest()).rejects.toMatchObject({ kind, reason });
    },
  );

  it('rejects an unknown reason even when the HTTP error code is valid', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'artifact_blocked',
              reason: 'internal_debug_state',
            },
          }),
          { status: 409 },
        ),
      ),
    );

    await expect(source.loadLatest()).rejects.toMatchObject({
      kind: 'blocked',
      reason: 'artifact_blocked',
    });
  });

  it('classifies invalid JSON without exposing parser details', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        new Response('{"/Users/example/private.json":', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const caught = await captureLoadError(source.loadLatest());

    expect(caught).toMatchObject({
      kind: 'unavailable',
      reason: 'artifact_response_invalid',
    });
    expect(String(caught)).not.toContain('/Users/example');
  });

  it('classifies decoder failures without exposing decoder details', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ...canonicalReportArtifactWireFixture,
            research_only: false,
          }),
          { status: 200 },
        ),
      ),
    );

    await expect(source.loadLatest()).rejects.toMatchObject({
      kind: 'unavailable',
      reason: 'artifact_payload_invalid',
    });
  });

  it('classifies fetch TypeError as a sanitized network failure', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockRejectedValue(
        new TypeError('Failed to fetch /Users/example/private.json'),
      ),
    );

    const caught = await captureLoadError(source.loadLatest());

    expect(caught).toMatchObject({
      kind: 'unavailable',
      reason: 'network_unavailable',
    });
    expect(String(caught)).not.toContain('/Users/example');
  });

  it('classifies AbortError separately from network failures', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockRejectedValue(
        new DOMException('/Users/example/private.json', 'AbortError'),
      ),
    );

    const caught = await captureLoadError(source.loadLatest());

    expect(caught).toMatchObject({
      kind: 'unavailable',
      reason: 'request_aborted',
    });
    expect(String(caught)).not.toContain('/Users/example');
  });

  it('classifies an aborted response body as request_aborted', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        responseWithJsonError(
          new DOMException('/Users/example/private.json', 'AbortError'),
        ),
      ),
    );

    const caught = await captureLoadError(source.loadLatest());

    expect(caught).toMatchObject({
      kind: 'unavailable',
      reason: 'request_aborted',
    });
    expect(String(caught)).not.toContain('/Users/example');
  });

  it('classifies a response-body TypeError as network_unavailable', async () => {
    const source = createHttpReportArtifactSource(
      vi.fn().mockResolvedValue(
        responseWithJsonError(
          new TypeError('Stream failed at /Users/example/private.json'),
        ),
      ),
    );

    const caught = await captureLoadError(source.loadLatest());

    expect(caught).toMatchObject({
      kind: 'unavailable',
      reason: 'network_unavailable',
    });
    expect(String(caught)).not.toContain('/Users/example');
  });

  it.each([
    [404, 'unavailable', 'artifact_not_found'],
    [409, 'blocked', 'artifact_blocked'],
    [422, 'unavailable', 'artifact_invalid'],
  ] as const)(
    'preserves HTTP %s classification when the error body stream raises TypeError',
    async (status, kind, reason) => {
      const source = createHttpReportArtifactSource(
        vi.fn().mockResolvedValue(
          responseWithJsonError(
            new TypeError('Stream failed at /Users/example/private.json'),
            status,
          ),
        ),
      );

      await expect(source.loadLatest()).rejects.toMatchObject({ kind, reason });
    },
  );

  it('treats an aborted signal as request_aborted across fetch realms', async () => {
    const controller = new AbortController();
    controller.abort();
    const source = createHttpReportArtifactSource(
      vi.fn().mockRejectedValue(new Error('foreign realm abort')),
    );

    await expect(source.loadLatest(controller.signal)).rejects.toMatchObject({
      kind: 'unavailable',
      reason: 'request_aborted',
    });
  });
});

async function captureLoadError(
  promise: Promise<unknown>,
): Promise<ReportArtifactLoadError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ReportArtifactLoadError);
    return error as ReportArtifactLoadError;
  }
  throw new Error('Expected ReportArtifactLoadError');
}

function responseWithJsonError(error: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockRejectedValue(error),
  } as unknown as Response;
}

const ALLOWED_HTTP_ERROR_REASONS = [
  [404, 'artifact_not_found', 'stock_analysis_artifact_missing'],
  [404, 'artifact_not_found', 'stock_analysis_report_missing'],
  [409, 'artifact_blocked', 'research_only_required'],
  [409, 'artifact_blocked', 'report_gate_research_only_required'],
  [409, 'artifact_blocked', 'report_safety_failed'],
  [409, 'artifact_blocked', 'research_boundary_required'],
  [422, 'artifact_invalid', 'artifact_type_missing'],
  [422, 'artifact_invalid', 'artifact_type_unsupported'],
  [422, 'artifact_invalid', 'forbidden_field'],
  [422, 'artifact_invalid', 'generated_at_invalid'],
  [422, 'artifact_invalid', 'key_claim_invalid'],
  [422, 'artifact_invalid', 'key_claim_provenance_missing'],
  [422, 'artifact_invalid', 'key_claims_missing'],
  [422, 'artifact_invalid', 'local_path_detected'],
  [422, 'artifact_invalid', 'manifest_json_invalid'],
  [422, 'artifact_invalid', 'manifest_object_required'],
  [422, 'artifact_invalid', 'manifest_path_invalid'],
  [422, 'artifact_invalid', 'manifest_unreadable'],
  [422, 'artifact_invalid', 'query_invalid'],
  [422, 'artifact_invalid', 'readiness_invalid'],
  [422, 'artifact_invalid', 'readiness_missing'],
  [422, 'artifact_invalid', 'report_gate_invalid'],
  [422, 'artifact_invalid', 'report_gate_missing'],
  [422, 'artifact_invalid', 'report_path_invalid'],
  [422, 'artifact_invalid', 'report_safety_invalid'],
  [422, 'artifact_invalid', 'reports_invalid'],
  [422, 'artifact_invalid', 'reports_missing'],
  [422, 'artifact_invalid', 'schema_version_missing'],
  [422, 'artifact_invalid', 'schema_version_unsupported'],
  [422, 'artifact_invalid', 'skeptical_review_invalid'],
  [422, 'artifact_invalid', 'skeptical_review_missing'],
  [422, 'artifact_invalid', 'source_coverage_invalid'],
  [422, 'artifact_invalid', 'source_coverage_missing'],
  [422, 'artifact_invalid', 'stock_analysis_report_unreadable'],
  [422, 'artifact_invalid', 'stock_name_invalid'],
  [422, 'artifact_invalid', 'symbol_invalid'],
] as const;
