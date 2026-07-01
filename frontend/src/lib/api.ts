const BASE_URL = "http://localhost:8000/api/v1";

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
}

export class ApiError extends Error {
  status: number;
  message: string;
  error?: string;
  request_id?: string;

  constructor(status: number, data: any) {
    super(data.message || "An unexpected error occurred");
    this.status = status;
    this.message = data.message || "An unexpected error occurred";
    this.error = data.error;
    this.request_id = data.request_id;
  }
}

async function request(endpoint: string, options: RequestOptions = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  // Set headers (avoid setting Content-Type for FormData uploads so browser generates boundary)
  const headers: Record<string, string> = {
    ...options.headers,
  };
  
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // Inject token if available
  const token = localStorage.getItem("niftymind_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    method: options.method || "GET",
    headers,
  };

  if (options.body) {
    if (options.body instanceof FormData) {
      config.body = options.body;
    } else {
      config.body = JSON.stringify(options.body);
    }
  }

  // Handle timeout
  let timeoutId: any = null;
  if (options.timeout) {
    const controller = new AbortController();
    config.signal = controller.signal;
    timeoutId = setTimeout(() => controller.abort(), options.timeout);
  }

  try {
    const response = await fetch(url, config);
    if (timeoutId) clearTimeout(timeoutId);

    if (response.status === 204) {
      return null;
    }

    const data = await response.json();
    
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem("niftymind_token");
        localStorage.removeItem("niftymind_user");
        window.location.href = "/login";
      }
      throw new ApiError(response.status, data);
    }
    
    return data;
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof ApiError) {
      throw error;
    }
    // Handle network or abort errors
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(504, { message: "Request timed out. Please try again." });
    }
    throw new ApiError(500, { message: "Network connection error. Is the server running?" });
  }
}

export const api = {
  get: (endpoint: string, options?: RequestOptions) => 
    request(endpoint, { ...options, method: "GET" }),
    
  post: (endpoint: string, body: any, options?: RequestOptions) => 
    request(endpoint, { ...options, method: "POST", body }),
    
  put: (endpoint: string, body: any, options?: RequestOptions) => 
    request(endpoint, { ...options, method: "PUT", body }),
    
  delete: (endpoint: string, options?: RequestOptions) => 
    request(endpoint, { ...options, method: "DELETE" }),
};
