import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WorkspacesPage from "@/app/workspaces/page";
import {
  APIKeyResponse,
  NotificationChannelResponse,
  NotificationDeliveryResponse,
  WorkspaceAuditLogResponse,
  WorkspaceMemberResponse,
  WorkspaceResponse,
  api,
} from "@/lib/api";

const mockWorkspaces: WorkspaceResponse[] = [
  {
    workspace_id: "11111111-1111-1111-1111-111111111111",
    name: "Default Workspace",
    slug: "default",
    description: "Primary workspace",
    is_default: true,
    member_count: 2,
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
  {
    workspace_id: "22222222-2222-2222-2222-222222222222",
    name: "Customer Support Swarm",
    slug: "customer-support-swarm",
    description: "Support tier agent evaluations",
    is_default: false,
    member_count: 1,
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
];

const mockMembers: WorkspaceMemberResponse[] = [
  {
    member_id: "33333333-3333-3333-3333-333333333333",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    user_email: "admin@example.com",
    role: "ADMIN",
    joined_at: "2026-11-08T10:00:00Z",
  },
  {
    member_id: "44444444-4444-4444-4444-444444444444",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    user_email: "engineer@example.com",
    role: "ENGINEER",
    joined_at: "2026-11-08T10:00:00Z",
  },
];

const mockAuditLogs: WorkspaceAuditLogResponse[] = [
  {
    log_id: "55555555-5555-5555-5555-555555555555",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    actor_email: "admin@example.com",
    action: "WORKSPACE_INITIALIZED",
    resource_type: "WORKSPACE",
    resource_id: "11111111-1111-1111-1111-111111111111",
    details: {},
    created_at: "2026-11-08T10:00:00Z",
  },
];

const mockApiKeys: APIKeyResponse[] = [
  {
    key_id: "key-123",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    name: "CI Ingest Key",
    key_prefix: "aep_live_abcd",
    role: "ENGINEER",
    created_by: "admin@example.com",
    created_at: "2026-11-08T10:00:00Z",
    expires_at: null,
    last_used_at: null,
    is_active: true,
  },
];

const mockChannels: NotificationChannelResponse[] = [
  {
    channel_id: "chan-1111",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    name: "Teams Governance Gate",
    channel_type: "TEAMS",
    webhook_url_masked: "https://company.webhook.office.com/webhookb2/****",
    events: ["POLICY_REJECTED", "POLICY_APPROVED"],
    is_active: true,
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
];

const mockDeliveries: NotificationDeliveryResponse[] = [
  {
    delivery_id: "deliv-111",
    channel_id: "chan-1111",
    workspace_id: "11111111-1111-1111-1111-111111111111",
    event_type: "POLICY_REJECTED",
    status: "DELIVERED",
    http_status: 200,
    error_message: null,
    delivered_at: "2026-11-08T11:00:00Z",
    created_at: "2026-11-08T11:00:00Z",
  },
];

describe("WorkspacesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "listApiKeys").mockResolvedValue(mockApiKeys);
    vi.spyOn(api, "listNotificationChannels").mockResolvedValue(mockChannels);
    vi.spyOn(api, "listNotificationHistory").mockResolvedValue(mockDeliveries);
  });

  it("loads and displays workspaces, active roster, and audit logs", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);

    render(<WorkspacesPage />);
    expect(screen.getByText(/Loading workspaces and memberships/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
      expect(screen.getByText("Customer Support Swarm")).toBeInTheDocument();
      expect(screen.getAllByText("admin@example.com").length).toBeGreaterThan(0);
      expect(screen.getByText("engineer@example.com")).toBeInTheDocument();
      expect(screen.getAllByText("ADMIN").length).toBeGreaterThan(0);
      expect(screen.getAllByText("ENGINEER").length).toBeGreaterThan(0);
      expect(screen.getByText("WORKSPACE_INITIALIZED")).toBeInTheDocument();
    });
  });

  it("opens create modal and submits a new workspace", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);
    vi.spyOn(api, "createWorkspace").mockResolvedValue(mockWorkspaces[1]);

    render(<WorkspacesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
    });

    const openModalBtn = screen.getByRole("button", { name: /\+ Create Workspace/i });
    fireEvent.click(openModalBtn);

    expect(screen.getByText("Create New Workspace")).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/e\.g\. Swarm Robotics/i);
    fireEvent.change(nameInput, { target: { value: "New Agent Lab" } });

    const createBtn = screen.getByRole("button", { name: "Create Workspace" });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(api.createWorkspace).toHaveBeenCalled();
    });
  });

  it("adds a new team member with RBAC role", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);
    vi.spyOn(api, "addWorkspaceMember").mockResolvedValue({
      member_id: "66666666-6666-6666-6666-666666666666",
      workspace_id: "11111111-1111-1111-1111-111111111111",
      user_email: "analyst@example.com",
      role: "VIEWER",
      joined_at: "2026-11-08T12:00:00Z",
    });

    render(<WorkspacesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
    });

    const emailInput = screen.getByPlaceholderText(/engineer@example\.com/i);
    fireEvent.change(emailInput, { target: { value: "analyst@example.com" } });

    const addBtn = screen.getByRole("button", { name: "Add" });
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(api.addWorkspaceMember).toHaveBeenCalledWith(
        mockWorkspaces[0].workspace_id,
        expect.objectContaining({
          user_email: "analyst@example.com",
        })
      );
    });
  });

  it("switches to API Keys tab and displays service accounts", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);
    vi.spyOn(api, "listApiKeys").mockResolvedValue(mockApiKeys);

    render(<WorkspacesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
    });

    const apiKeysTabBtn = screen.getByRole("button", { name: /API Keys & Service Accounts/i });
    fireEvent.click(apiKeysTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Workspace API Keys & Service Accounts")).toBeInTheDocument();
      expect(screen.getByText("CI Ingest Key")).toBeInTheDocument();
      expect(screen.getByText(/aep_live_abcd/)).toBeInTheDocument();
    });
  });

  it("switches to Notifications tab and renders webhook channels and history", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);
    vi.spyOn(api, "listNotificationChannels").mockResolvedValue(mockChannels);
    vi.spyOn(api, "listNotificationHistory").mockResolvedValue(mockDeliveries);

    render(<WorkspacesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
    });

    const notifTabBtn = screen.getByRole("button", { name: /Notifications & Alerting/i });
    fireEvent.click(notifTabBtn);

    await waitFor(() => {
      expect(screen.getByTestId("notifications-section")).toBeInTheDocument();
      expect(screen.getByText("Teams Governance Gate")).toBeInTheDocument();
      expect(screen.getByText("Microsoft Teams")).toBeInTheDocument();
      expect(screen.getAllByText("POLICY_REJECTED").length).toBeGreaterThan(0);
      expect(screen.getByText("DELIVERED")).toBeInTheDocument();
    });
  });

  it("switches to OTEL Integrations tab and renders collector endpoints and framework snippets", async () => {
    vi.spyOn(api, "listWorkspaces").mockResolvedValue(mockWorkspaces);
    vi.spyOn(api, "listWorkspaceMembers").mockResolvedValue(mockMembers);
    vi.spyOn(api, "listWorkspaceAuditLogs").mockResolvedValue(mockAuditLogs);
    vi.spyOn(api, "listNotificationChannels").mockResolvedValue(mockChannels);

    render(<WorkspacesPage />);
    await waitFor(() => {
      expect(screen.getAllByText("Default Workspace").length).toBeGreaterThan(0);
    });

    const otelTabBtn = screen.getByRole("button", { name: /OTEL Integrations/i });
    fireEvent.click(otelTabBtn);

    await waitFor(() => {
      expect(screen.getByTestId("otel-integrations-section")).toBeInTheDocument();
      expect(screen.getByText("OpenTelemetry Native Collector Receiver")).toBeInTheDocument();
      expect(screen.getByText("/api/v1/otel/collector")).toBeInTheDocument();
      expect(screen.getByText("localhost:4317")).toBeInTheDocument();
      expect(screen.getByText("Framework & Collector Setup Snippets")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /LangGraph/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /CrewAI/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /AutoGen/i })).toBeInTheDocument();
    });
  });
});
