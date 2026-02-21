/**
 * SSE Client for Agent Streaming (B1.4 - Kill Switch)
 *
 * IMPORTANT: This class is NOT a singleton. Create one instance per active
 * stream and clean it up when done. Use the useSSEStream hook instead of
 * instantiating directly.
 *
 * The client handles:
 * - EventSource connection management
 * - Typed event parsing
 * - Automatic reconnection (up to 3 attempts)
 * - Connection state callbacks
 * - Artifact created events (B1.3)
 * - Run terminated events (B1.4)
 */

import type {
  TokenEvent,
  ToolStartEvent,
  ToolEndEvent,
  ErrorEvent,
  DoneEvent,
  ArtifactCreatedEvent,
  RunTerminatedEvent,
  // B2.2 Multi-brain events
  ClassificationEvent,
  BrainThinkingEvent,
  DeliberationRoundEvent,
  ConsensusReachedEvent,
  ConsensusFailedEvent,
  EscalationRequiredEvent,
} from "@/lib/api/types";

// =============================================================================
// Types
// =============================================================================

export interface SSEClientHandlers {
  onToken: (data: TokenEvent) => void;
  onToolStart: (data: ToolStartEvent) => void;
  onToolEnd: (data: ToolEndEvent) => void;
  onError: (data: ErrorEvent) => void;
  onDone: (data: DoneEvent) => void;
  onConnectionChange: (connected: boolean) => void;
  // B1.3 - Artifact created event (optional for backwards compatibility)
  onArtifactCreated?: (data: ArtifactCreatedEvent) => void;
  // B1.4 - Run terminated event (kill switch)
  onRunTerminated?: (data: RunTerminatedEvent) => void;
  // B2.2 - Multi-brain events
  onClassification?: (data: ClassificationEvent) => void;
  onBrainThinking?: (data: BrainThinkingEvent) => void;
  onDeliberationRound?: (data: DeliberationRoundEvent) => void;
  onConsensusReached?: (data: ConsensusReachedEvent) => void;
  onConsensusFailed?: (data: ConsensusFailedEvent) => void;
  onEscalationRequired?: (data: EscalationRequiredEvent) => void;
}

// =============================================================================
// SSE Client
// =============================================================================

export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 2000; // 2 seconds
  private cleanedUp = false;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(
    private url: string,
    private handlers: SSEClientHandlers
  ) {}

  /**
   * Establish SSE connection to the server.
   */
  connect(): void {
    if (this.cleanedUp) {
      console.warn("SSEClient: Attempted to connect after cleanup");
      return;
    }

    // Clean up any existing connection
    this.closeEventSource();

    try {
      this.eventSource = new EventSource(this.url);
      this.setupEventListeners();
    } catch (error) {
      console.error("SSEClient: Failed to create EventSource", error);
      this.handlers.onConnectionChange(false);
      this.handleReconnect();
    }
  }

  /**
   * Close the connection and clean up resources.
   */
  cleanup(): void {
    this.cleanedUp = true;
    this.closeEventSource();

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  /**
   * Check if the client is connected.
   */
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private closeEventSource(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private setupEventListeners(): void {
    if (!this.eventSource) return;

    this.eventSource.onopen = () => {
      console.log("SSEClient: Connection opened");
      this.reconnectAttempts = 0;
      this.handlers.onConnectionChange(true);
    };

    this.eventSource.onerror = (event) => {
      console.error("SSEClient: Connection error", event);
      this.handlers.onConnectionChange(false);

      // EventSource auto-closes on error, track attempts for manual fallback
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.handleReconnect();
      }
    };

    // Type-safe event listeners
    this.eventSource.addEventListener("token", (e: MessageEvent) => {
      this.handleEvent("token", e, this.handlers.onToken);
    });

    this.eventSource.addEventListener("tool_start", (e: MessageEvent) => {
      this.handleEvent("tool_start", e, this.handlers.onToolStart);
    });

    this.eventSource.addEventListener("tool_end", (e: MessageEvent) => {
      this.handleEvent("tool_end", e, this.handlers.onToolEnd);
    });

    this.eventSource.addEventListener("error", (e: MessageEvent) => {
      // Note: This is for SSE "error" events from the server, not connection errors
      if (e.data) {
        this.handleEvent("error", e, this.handlers.onError);
      }
    });

    this.eventSource.addEventListener("done", (e: MessageEvent) => {
      this.handleEvent("done", e, this.handlers.onDone);
    });

    // B1.3 - Artifact created event
    if (this.handlers.onArtifactCreated) {
      this.eventSource.addEventListener("artifact_created", (e: MessageEvent) => {
        this.handleEvent("artifact_created", e, this.handlers.onArtifactCreated!);
      });
    }

    // B1.4 - Run terminated event (kill switch)
    if (this.handlers.onRunTerminated) {
      this.eventSource.addEventListener("run_terminated", (e: MessageEvent) => {
        this.handleEvent("run_terminated", e, this.handlers.onRunTerminated!);
      });
    }

    // B2.2 - Multi-brain events
    if (this.handlers.onClassification) {
      this.eventSource.addEventListener("classification", (e: MessageEvent) => {
        this.handleEvent("classification", e, this.handlers.onClassification!);
      });
    }

    if (this.handlers.onBrainThinking) {
      this.eventSource.addEventListener("brain_thinking", (e: MessageEvent) => {
        this.handleEvent("brain_thinking", e, this.handlers.onBrainThinking!);
      });
    }

    if (this.handlers.onDeliberationRound) {
      this.eventSource.addEventListener("deliberation_round", (e: MessageEvent) => {
        this.handleEvent("deliberation_round", e, this.handlers.onDeliberationRound!);
      });
    }

    if (this.handlers.onConsensusReached) {
      this.eventSource.addEventListener("consensus_reached", (e: MessageEvent) => {
        this.handleEvent("consensus_reached", e, this.handlers.onConsensusReached!);
      });
    }

    if (this.handlers.onConsensusFailed) {
      this.eventSource.addEventListener("consensus_failed", (e: MessageEvent) => {
        this.handleEvent("consensus_failed", e, this.handlers.onConsensusFailed!);
      });
    }

    if (this.handlers.onEscalationRequired) {
      this.eventSource.addEventListener("escalation_required", (e: MessageEvent) => {
        this.handleEvent("escalation_required", e, this.handlers.onEscalationRequired!);
      });
    }
  }

  private handleEvent<T>(
    eventType: string,
    event: MessageEvent,
    handler: (data: T) => void
  ): void {
    try {
      const data = JSON.parse(event.data) as T;
      handler(data);
    } catch (error) {
      console.error(`SSEClient: Failed to parse ${eventType} event`, error);
    }
  }

  private handleReconnect(): void {
    if (this.cleanedUp) return;

    this.reconnectAttempts++;

    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      console.error("SSEClient: Max reconnect attempts reached");
      return;
    }

    console.log(
      `SSEClient: Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`
    );

    this.reconnectTimeout = setTimeout(() => {
      if (!this.cleanedUp) {
        this.connect();
      }
    }, this.reconnectDelay);
  }
}
