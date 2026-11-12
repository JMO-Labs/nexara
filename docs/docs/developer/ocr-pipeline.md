# OCR pipeline

Uploaded images are optionally OCR'd in the background so their text is searchable.

## Flow

1. `MediaService.upload` stores the file and enqueues `generate_thumbnail`.
2. `enqueue_ocr` then queues `app.tasks.ai_tasks.ocr_process_image(media_id, community_id)`
   on the `media` queue (1-hour time limit), only if the content type is `image/*`
   and `AI_PROVIDER` is set.
3. The task (`app/services/ai/ocr.py::run_ocr`) loads the media, skips non-images,
   calls `AIProvider.vision(bytes, "Extract all visible text. Return only text, one line per element.", max_tokens=2000)`
   and stores the result in `media_ai_metadata` with `processed_at`.

## Error handling

OCR is an enhancement and never fails an upload. Outcomes are counted in the
`nexara_ocr_processed_total{status}` Prometheus metric.

| Situation | Status | Behaviour |
|---|---|---|
| AI not configured / not an image | `skipped` | nothing stored |
| Budget exhausted | `budget_exhausted` | logged, nothing stored |
| Provider or storage error | `error` | warning logged, nothing stored |
| Success | `processed` | row created |

Media stays visible and searchable by filename in every case.

## Schema

`media_ai_metadata`: `media_id` (PK, FK media, cascade), `ocr_text`, `ocr_fts`
(generated `to_tsvector('english', ocr_text)`, GIN index `idx_media_ai_metadata_ocr_fts`),
`description`, `tags` (JSONB), `processed_at`, `community_id`, `created_at`.
`MediaAIRepository.search_by_fts` queries `ocr_fts` with `websearch_to_tsquery`.

## Configuration

`AI_PROVIDER` (empty = disabled). Providers implement the `AIProvider` protocol in
`app/services/ai/provider.py` and register in `_PROVIDERS`; none ship yet.
