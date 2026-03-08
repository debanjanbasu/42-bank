declare module 'event-source-polyfill' {
  export interface EventSourcePolyfillInit {
    headers?: Record<string, string>;
    method?: string;
    body?: string;
    withCredentials?: boolean;
  }

  export class EventSourcePolyfill extends EventTarget {
    constructor(url: string, init?: EventSourcePolyfillInit);
    onmessage: ((event: MessageEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
    onopen: ((event: Event) => void) | null;
    readyState: number;
    url: string;
    close(): void;
  }
}
