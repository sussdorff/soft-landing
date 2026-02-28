import type { DashboardAPI } from "../types";
import { createMockAdapter } from "./mock-adapter";
import { createApiAdapter } from "./api-adapter";

const useMocks = import.meta.env.VITE_USE_MOCKS === "true";

export const api: DashboardAPI = useMocks
  ? createMockAdapter()
  : createApiAdapter();
