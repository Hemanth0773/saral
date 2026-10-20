/**
 * Guards a user action against being started twice.
 *
 * The Simplify button is disabled while a request is running, but a
 * disabled attribute alone is not a guarantee: two clicks that land in the
 * same event loop tick would both see the pre-update state and both would
 * start a request. This guard makes "one in-flight request per action"
 * explicit and testable.
 */
export interface InFlightGuard {
  /** Returns true when the action may start, false when one is already running. */
  tryStart(): boolean;
  /** Marks the action as finished so it can be started again. */
  finish(): void;
  /** Whether an action is currently running. */
  readonly isRunning: boolean;
}

export function createInFlightGuard(): InFlightGuard {
  let running = false;

  return {
    tryStart(): boolean {
      if (running) return false;
      running = true;
      return true;
    },
    finish(): void {
      running = false;
    },
    get isRunning(): boolean {
      return running;
    },
  };
}
