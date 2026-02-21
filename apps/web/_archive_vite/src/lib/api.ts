/**
 * API Client for FastAPI Backend
 * Base URL: http://localhost:8000
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ============================================================================
// Types
// ============================================================================

/**
 * Data required to submit a new waitlist signup.
 * @property email - Valid email address (required)
 * @property name - User's full name (optional)
 * @property company - User's company name (optional)
 * @property role - User's job role/title (optional)
 */
export interface WaitlistSignupData {
  email: string;
  name?: string;
  company?: string;
  role?: string;
}

/**
 * Response returned after successful waitlist submission.
 * @property message - Success message from the API
 * @property email - Confirmed email address
 * @property position - User's position in the waitlist queue (optional)
 */
export interface WaitlistSignupResponse {
  message: string;
  email: string;
  position?: number;
}

/**
 * Summary data for an AI agent's activity.
 * @property agent_name - Unique identifier for the agent
 * @property last_run - ISO timestamp of last execution (null if never run)
 * @property status - Current operational status
 * @property items_processed - Total number of items processed
 * @property avg_confidence - Average confidence score (0-1)
 * @property sources - Number of data sources used
 * @property error_count - Total errors encountered
 */
export interface AgentSummary {
  agent_name: string;
  last_run: string | null;
  status: "active" | "idle" | "error";
  items_processed: number;
  avg_confidence: number;
  sources: number;
  error_count: number;
}

/**
 * Newsletter content item with metadata.
 * @property id - Unique identifier (UUID)
 * @property title - Newsletter title
 * @property slug - URL-friendly slug
 * @property content_type - Type of content (e.g., "newsletter", "deep-dive")
 * @property body - Full content body (Markdown)
 * @property published_at - ISO timestamp of publication
 * @property metadata - Additional metadata (optional)
 */
export interface NewsletterItem {
  id: string;
  title: string;
  slug: string;
  content_type: string;
  body: string;
  published_at: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Submit a new email to the waitlist.
 *
 * Sends a POST request to the backend API to register a user for the founding member waitlist.
 * The API validates the email, checks for duplicates, and assigns a position in the queue.
 *
 * @param data - Waitlist signup data (email required, name/company/role optional)
 * @returns Promise resolving to the signup response with confirmation message and position
 * @throws {Error} If the API request fails or email is invalid/already registered
 *
 * @example
 * ```typescript
 * const response = await submitWaitlist({
 *   email: "user@example.com",
 *   name: "João Silva"
 * });
 * console.log(response.position); // 248
 * ```
 */
export async function submitWaitlist(data: WaitlistSignupData): Promise<WaitlistSignupResponse> {
  const response = await fetch(`${API_BASE}/api/waitlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to submit to waitlist" }));
    throw new Error(error.detail || "Failed to submit to waitlist");
  }

  return response.json();
}

/**
 * Fetch the current number of signups in the waitlist.
 *
 * Retrieves the total count of users who have signed up for the founding member waitlist.
 * This function includes graceful error handling and returns a fallback value (247) if the
 * API is unavailable or the request fails.
 *
 * @returns Promise resolving to the waitlist count (or 247 as fallback)
 * @throws Never throws - errors are logged and fallback value is returned
 *
 * @example
 * ```typescript
 * const count = await fetchWaitlistCount();
 * console.log(`${count} pessoas na fila`);
 * ```
 */
export async function fetchWaitlistCount(): Promise<number> {
  try {
    const response = await fetch(`${API_BASE}/api/waitlist/count`);

    if (!response.ok) {
      console.warn("Failed to fetch waitlist count, using fallback");
      return 247; // Fallback number
    }

    const data = await response.json();
    return data.count || 247;
  } catch (error) {
    console.warn("Error fetching waitlist count:", error);
    return 247; // Fallback number
  }
}

/**
 * Fetch summary data for all AI agents.
 *
 * Retrieves operational metrics for all active AI agents in the system, including
 * status, last run time, items processed, confidence scores, and error counts.
 * Used for displaying agent activity on dashboards and transparency pages.
 *
 * @returns Promise resolving to an array of agent summaries (empty array if API fails)
 * @throws Never throws - errors are logged and empty array is returned
 *
 * @example
 * ```typescript
 * const agents = await fetchAgentSummaries();
 * agents.forEach(agent => {
 *   console.log(`${agent.agent_name}: ${agent.status}`);
 * });
 * ```
 */
export async function fetchAgentSummaries(): Promise<AgentSummary[]> {
  try {
    const response = await fetch(`${API_BASE}/api/agents/summary`);

    if (!response.ok) {
      console.warn("Failed to fetch agent summaries");
      return [];
    }

    return response.json();
  } catch (error) {
    console.warn("Error fetching agent summaries:", error);
    return [];
  }
}

/**
 * Fetch the most recently published newsletter.
 *
 * Retrieves the latest newsletter content including title, body (Markdown), publication date,
 * and associated metadata. Used for displaying newsletter previews on the homepage.
 *
 * @returns Promise resolving to the newsletter item (null if not found or API fails)
 * @throws Never throws - errors are logged and null is returned
 *
 * @example
 * ```typescript
 * const newsletter = await fetchLatestNewsletter();
 * if (newsletter) {
 *   console.log(newsletter.title);
 * }
 * ```
 */
export async function fetchLatestNewsletter(): Promise<NewsletterItem | null> {
  try {
    const response = await fetch(`${API_BASE}/api/content/newsletter/latest`);

    if (!response.ok) {
      console.warn("Failed to fetch latest newsletter");
      return null;
    }

    return response.json();
  } catch (error) {
    console.warn("Error fetching latest newsletter:", error);
    return null;
  }
}

/**
 * Perform a health check on the API backend.
 *
 * Sends a simple GET request to the /health endpoint to verify the API is reachable
 * and responding correctly. Useful for monitoring and status checks.
 *
 * @returns Promise resolving to true if API is healthy, false otherwise
 * @throws Never throws - errors are logged and false is returned
 *
 * @example
 * ```typescript
 * const isHealthy = await healthCheck();
 * if (!isHealthy) {
 *   console.warn("API está offline");
 * }
 * ```
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: "GET",
    });
    return response.ok;
  } catch (error) {
    console.warn("API health check failed:", error);
    return false;
  }
}
