/**
 * @file composables/useEventBus.ts
 * @brief Registry-based SSE event dispatcher.
 *
 * Stores self-register handlers for specific SSE event types via
 * ``on()``.  The layout simply calls ``dispatch()`` for every incoming
 * SSE event, and the bus routes it to all registered handlers.
 *
 * This decouples stores from the layout -- adding real-time support to
 * a new feature only requires calling ``on()`` inside that feature's
 * store; no changes to the layout or SSE composable are needed.
 */

/** @brief Callback signature for SSE event handlers. */
export type SseEventHandler = (data: unknown) => void;

/**
 * @brief Module-level handler registry, shared across all callers.
 *
 * Maps SSE event type strings to their registered handler sets.
 * Using a module-scoped Map ensures handlers persist across
 * component re-renders while remaining tree-shakeable.
 */
const handlers = new Map<string, Set<SseEventHandler>>();

/**
 * @brief Access the SSE event bus.
 *
 * @returns ``on`` to register a handler, ``off`` to remove one,
 *          and ``dispatch`` to fire an event to all handlers.
 */
export function useEventBus() {
  /**
   * @brief Register a handler for a specific SSE event type.
   *
   * @param eventType - SSE event name (e.g. ``SSE_EVENT.FEED_UPDATE``).
   * @param handler   - Callback receiving the parsed event data.
   * @returns Unsubscribe function that removes this handler.
   */
  function on(eventType: string, handler: SseEventHandler): () => void {
    if (!handlers.has(eventType)) {
      handlers.set(eventType, new Set());
    }
    handlers.get(eventType)!.add(handler);
    return () => handlers.get(eventType)?.delete(handler);
  }

  /**
   * @brief Remove a previously registered handler.
   *
   * @param eventType - SSE event name.
   * @param handler   - The exact function reference to remove.
   */
  function off(eventType: string, handler: SseEventHandler): void {
    handlers.get(eventType)?.delete(handler);
  }

  /**
   * @brief Dispatch an SSE event to all registered handlers.
   *
   * Called by the layout's SSE callback for every incoming event.
   *
   * @param eventType - SSE event name.
   * @param data      - Parsed event payload.
   */
  function dispatch(eventType: string, data: unknown): void {
    const set = handlers.get(eventType);
    if (set) {
      set.forEach((fn) => fn(data));
    }
  }

  return { on, off, dispatch };
}
