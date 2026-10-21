/**
 * Minimal ambient declarations for the subset of the Chrome extension API that
 * Saral uses. The project intentionally avoids the `@types/chrome` dependency
 * so the extension stays self-contained and installable without extra packages.
 */
declare namespace chrome {
  namespace runtime {
    interface MessageSender {
      tab?: tabs.Tab;
      frameId?: number;
      id?: string;
    }

    const lastError: { message?: string } | undefined;

    function getURL(path: string): string;
    function sendMessage<TRequest, TResponse>(
      message: TRequest,
      callback?: (response: TResponse) => void,
    ): Promise<TResponse>;
    function sendMessage<TRequest, TResponse>(
      message: TRequest,
      options: { tabId?: number },
      callback?: (response: TResponse) => void,
    ): Promise<TResponse>;
    function openOptionsPage(callback?: () => void): void;

    namespace onMessage {
      interface MessageEvent {
        addListener<TRequest = unknown, TResponse = unknown>(
          listener: (
            message: TRequest,
            sender: MessageSender,
            sendResponse: (response?: TResponse) => void,
          ) => boolean | void,
        ): void;
        removeListener(listener: (...args: never[]) => unknown): void;
      }

      const addListener: MessageEvent['addListener'];
      const removeListener: MessageEvent['removeListener'];
    }
  }

  namespace tabs {
    interface Tab {
      id?: number;
      url?: string;
      title?: string;
      active?: boolean;
      windowId?: number;
      status?: string;
    }

    interface QueryInfo {
      active?: boolean;
      currentWindow?: boolean;
      windowId?: number;
      url?: string | string[];
    }

    function query(
      queryInfo: QueryInfo,
      callback?: (tabs: Tab[]) => void,
    ): Promise<Tab[]>;
    function sendMessage<TRequest, TResponse>(
      tabId: number,
      message: TRequest,
      callback?: (response: TResponse) => void,
    ): Promise<TResponse>;
    function create(
      createProperties: { url?: string; active?: boolean },
      callback?: (tab: Tab) => void,
    ): Promise<Tab>;
  }

  namespace scripting {
    interface InjectionTarget {
      tabId: number;
      frameIds?: number[];
      allFrames?: boolean;
    }

    function executeScript<TResult>(
      injection: { target: InjectionTarget; files: string[] },
    ): Promise<{ frameId: number; result: TResult }[]>;
  }

  namespace storage {
    namespace local {
      function get(
        keys: string | string[] | Record<string, unknown> | null,
        callback?: (items: Record<string, unknown>) => void,
      ): Promise<Record<string, unknown>>;
      function set(
        items: Record<string, unknown>,
        callback?: () => void,
      ): Promise<void>;
      function remove(keys: string | string[], callback?: () => void): Promise<void>;
    }
  }

  namespace permissions {
    function contains(
      permissions: { origins?: string[]; permissions?: string[] },
      callback?: (result: boolean) => void,
    ): Promise<boolean>;
    function request(
      permissions: { origins?: string[]; permissions?: string[] },
      callback?: (granted: boolean) => void,
    ): Promise<boolean>;
    function remove(
      permissions: { origins?: string[]; permissions?: string[] },
      callback?: (granted: boolean) => void,
    ): Promise<boolean>;
  }

  namespace action {
    function openPopup(callback?: () => void): Promise<void>;
  }

  namespace commands {
    const onCommand: {
      addListener(listener: (command: string) => void): void;
      removeListener(listener: (command: string) => void): void;
    };
  }
}
