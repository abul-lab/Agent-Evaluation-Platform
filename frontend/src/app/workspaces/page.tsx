"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  APIKeyCreateRequest,
  APIKeyCreateResponse,
  APIKeyResponse,
  NotificationChannelCreateRequest,
  NotificationChannelResponse,
  NotificationChannelType,
  NotificationDeliveryResponse,
  NotificationEventType,
  NotificationTestResponse,
  ServiceAccountRole,
  WorkspaceAuditLogResponse,
  WorkspaceCreateRequest,
  WorkspaceMemberResponse,
  WorkspaceResponse,
  WorkspaceRole,
  api,
} from "@/lib/api";

const ALL_NOTIFICATION_EVENTS: { id: NotificationEventType; label: string; category: string }[] = [
  { id: "EVALUATION_COMPLETED", label: "Evaluation Completed", category: "Evaluation" },
  { id: "EVALUATION_FAILED", label: "Evaluation Failed", category: "Evaluation" },
  { id: "REGRESSION_DETECTED", label: "Regression Detected", category: "Quality" },
  { id: "POLICY_APPROVED", label: "Policy Approved (Gating Passed)", category: "Governance" },
  { id: "POLICY_REJECTED", label: "Policy Rejected (Gating Blocked)", category: "Governance" },
  { id: "SECRET_EXPOSURE", label: "Secret / Credential Leaked", category: "Security" },
  { id: "CRITICAL_FINDING", label: "Critical Finding Detected", category: "Security" },
  { id: "API_KEY_CREATED", label: "Service Account Key Generated", category: "Access & Auth" },
  { id: "API_KEY_REVOKED", label: "Service Account Key Revoked", category: "Access & Auth" },
];

const OTEL_FRAMEWORKS = [
  {
    id: "collector" as const,
    name: "OpenTelemetry Collector",
    tag: "YAML Config",
    lang: "yaml",
    description: "Standard otel-collector-config.yaml forwarding agent traces into AEP.",
    code: `receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 100

exporters:
  otlphttp/aep:
    endpoint: http://localhost:8000/api/v1/otel/collector
    headers:
      Authorization: "Bearer \${AEP_API_KEY}"
      # Alternative: x-api-key: "\${AEP_API_KEY}"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/aep]`,
  },
  {
    id: "langgraph" as const,
    name: "LangGraph",
    tag: "Python SDK",
    lang: "python",
    description: "Streams LangGraph node execution and agent state graphs directly into AEP.",
    code: `import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# 1. Initialize OpenTelemetry Provider
resource = Resource.create({"service.name": "langgraph-agent", "framework": "langgraph"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint="http://localhost:8000/api/v1/otel/collector",
    headers={"Authorization": f"Bearer {os.getenv('AEP_API_KEY', 'aep_live_...')}"}
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# 2. Run LangGraph Workflow (Traces are automatically converted to CATS and evaluated)
# app = workflow.compile()
# result = app.invoke({"messages": [...]})`,
  },
  {
    id: "crewai" as const,
    name: "CrewAI",
    tag: "Python SDK",
    lang: "python",
    description: "Captures multi-agent crew handoffs, role delegation, and tool executions.",
    code: `import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "crewai-multi-agent", "framework": "crewai"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint="http://localhost:8000/api/v1/otel/collector",
    headers={"x-api-key": os.getenv("AEP_API_KEY", "aep_live_...")}
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# Crew runs stream into AEP with automatic task-level scorecard audit
# crew = Crew(agents=[analyst, writer], tasks=[research, draft])
# result = crew.kickoff()`,
  },
  {
    id: "autogen" as const,
    name: "AutoGen",
    tag: "Python SDK",
    lang: "python",
    description: "Captures conversable agent interactions, group chat routing, and code execution.",
    code: `import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "autogen-groupchat", "framework": "autogen"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint="http://localhost:8000/api/v1/otel/collector",
    headers={"Authorization": f"Bearer {os.getenv('AEP_API_KEY', 'aep_live_...')}"}
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# AutoGen multi-agent turns automatically parsed and persisted into active workspace`,
  },
  {
    id: "openai" as const,
    name: "OpenAI Agents SDK",
    tag: "Python SDK",
    lang: "python",
    description: "Captures OpenAI Agent Swarm routines, handoffs, and tool execution lifecycles.",
    code: `import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

provider = TracerProvider(
    resource=Resource.create({"service.name": "openai-swarm", "framework": "openai_agents"})
)
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="http://localhost:8000/api/v1/otel/collector",
            headers={"Authorization": f"Bearer {os.getenv('AEP_API_KEY', 'aep_live_...')}"}
        )
    )
)
trace.set_tracer_provider(provider)

# Runs stream to AEP with deterministic evaluation scorecards`,
  },
  {
    id: "llamaindex" as const,
    name: "LlamaIndex",
    tag: "OpenInference",
    lang: "python",
    description: "Direct instrumentation for retrieval steps, query engines, and agentic workflows.",
    code: `import os
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="http://localhost:8000/api/v1/otel/collector",
            headers={"Authorization": f"Bearer {os.getenv('AEP_API_KEY', 'aep_live_...')}"}
        )
    )
)
LlamaIndexInstrumentor().instrument(tracer_provider=provider)

# All query engine and agent steps stream directly into AEP`,
  },
  {
    id: "generic" as const,
    name: "Generic OpenTelemetry",
    tag: "Standard OTLP",
    lang: "python",
    description: "Standard OpenTelemetry Python SDK trace publisher for any custom agent system.",
    code: `import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="http://localhost:8000/api/v1/otel/collector",
            headers={"Authorization": f"Bearer {os.getenv('AEP_API_KEY', 'aep_live_...')}"}
        )
    )
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agent-core")

with tracer.start_as_current_span("agent_execution") as span:
    span.set_attribute("agent.status", "completed")`,
  },
];

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>("");
  const [members, setMembers] = useState<WorkspaceMemberResponse[]>([]);
  const [auditLogs, setAuditLogs] = useState<WorkspaceAuditLogResponse[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKeyResponse[]>([]);
  const [channels, setChannels] = useState<NotificationChannelResponse[]>([]);
  const [deliveries, setDeliveries] = useState<NotificationDeliveryResponse[]>([]);
  const [activeTab, setActiveTab] = useState<"team" | "api_keys" | "notifications" | "otel" | "audit">("team");
  const [selectedOtelFramework, setSelectedOtelFramework] = useState<
    "collector" | "langgraph" | "crewai" | "autogen" | "openai" | "llamaindex" | "generic"
  >("collector");
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Workspace Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [newWsSlug, setNewWsSlug] = useState("");
  const [newWsDesc, setNewWsDesc] = useState("");
  const [creatingWs, setCreatingWs] = useState(false);

  // Add Member State
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<WorkspaceRole>("ENGINEER");
  const [addingMember, setAddingMember] = useState(false);

  // API Key State
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyRole, setNewKeyRole] = useState<ServiceAccountRole>("ENGINEER");
  const [newKeyExpiryDays, setNewKeyExpiryDays] = useState<number | null>(90);
  const [creatingKey, setCreatingKey] = useState(false);
  const [createdKeyResult, setCreatedKeyResult] = useState<APIKeyCreateResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Notification State
  const [showCreateChannelModal, setShowCreateChannelModal] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const [newChannelType, setNewChannelType] = useState<NotificationChannelType>("SLACK");
  const [newChannelUrl, setNewChannelUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<NotificationEventType[]>(
    ALL_NOTIFICATION_EVENTS.map((e) => e.id)
  );
  const [creatingChannel, setCreatingChannel] = useState(false);
  const [testingChannelId, setTestingChannelId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<NotificationTestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const fetchWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listWorkspaces();
      setWorkspaces(data);
      if (data.length > 0 && !activeWorkspaceId) {
        const defaultWs = data.find((w) => w.is_default) || data[0];
        setActiveWorkspaceId(defaultWs.workspace_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspaces");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspaceId]);

  const fetchWorkspaceDetails = useCallback(async (wsId: string) => {
    try {
      const [membersData, logsData, keysData, channelsData, deliveriesData] = await Promise.all([
        api.listWorkspaceMembers(wsId).catch(() => []),
        api.listWorkspaceAuditLogs(wsId).catch(() => []),
        api.listApiKeys(wsId).catch(() => []),
        api.listNotificationChannels(wsId).catch(() => []),
        api.listNotificationHistory(wsId).catch(() => []),
      ]);
      setMembers(membersData);
      setAuditLogs(logsData);
      setApiKeys(keysData);
      setChannels(channelsData);
      setDeliveries(deliveriesData);
    } catch (err) {
      console.error("Failed to load workspace details:", err);
    }
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  useEffect(() => {
    if (activeWorkspaceId) {
      fetchWorkspaceDetails(activeWorkspaceId);
    }
  }, [activeWorkspaceId, fetchWorkspaceDetails]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;

    try {
      setCreatingWs(true);
      const req: WorkspaceCreateRequest = {
        name: newWsName.trim(),
        slug: newWsSlug.trim() || undefined,
        description: newWsDesc.trim(),
        is_default: false,
      };
      const created = await api.createWorkspace(req);
      setWorkspaces((prev) => [...prev.filter((w) => w.workspace_id !== created.workspace_id), created]);
      setActiveWorkspaceId(created.workspace_id);
      setShowCreateModal(false);
      setNewWsName("");
      setNewWsSlug("");
      setNewWsDesc("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setCreatingWs(false);
    }
  };

  const handleDeleteWorkspace = async (wsId: string) => {
    if (!confirm("Are you sure you want to delete this workspace?")) return;

    try {
      await api.deleteWorkspace(wsId);
      setWorkspaces((prev) => prev.filter((w) => w.workspace_id !== wsId));
      if (activeWorkspaceId === wsId) {
        const remaining = workspaces.filter((w) => w.workspace_id !== wsId);
        if (remaining.length > 0) {
          setActiveWorkspaceId(remaining[0].workspace_id);
        } else {
          setActiveWorkspaceId("");
        }
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete workspace");
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberEmail.trim() || !activeWorkspaceId) return;

    try {
      setAddingMember(true);
      const member = await api.addWorkspaceMember(activeWorkspaceId, {
        user_email: newMemberEmail.trim(),
        role: newMemberRole,
      });
      setMembers((prev) => [...prev, member]);
      setNewMemberEmail("");
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add member");
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm("Remove this member from the workspace?")) return;

    try {
      await api.removeWorkspaceMember(activeWorkspaceId, memberId);
      setMembers((prev) => prev.filter((m) => m.member_id !== memberId));
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim() || !activeWorkspaceId) return;

    try {
      setCreatingKey(true);
      const req: APIKeyCreateRequest = {
        name: newKeyName.trim(),
        workspace_id: activeWorkspaceId,
        role: newKeyRole,
        expires_in_days: newKeyExpiryDays,
      };
      const result = await api.createApiKey(req);
      setCreatedKeyResult(result);
      setShowCreateKeyModal(false);
      setNewKeyName("");
      setNewKeyRole("ENGINEER");
      setNewKeyExpiryDays(90);
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create API key");
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeApiKey = async (keyId: string) => {
    if (!confirm("Are you sure you want to revoke this API key? This action is irreversible.")) return;

    try {
      await api.revokeApiKey(keyId);
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to revoke API key");
    }
  };

  const handleCreateChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChannelName.trim() || !newChannelUrl.trim() || !activeWorkspaceId) return;

    try {
      setCreatingChannel(true);
      const req: NotificationChannelCreateRequest = {
        name: newChannelName.trim(),
        channel_type: newChannelType,
        webhook_url: newChannelUrl.trim(),
        events: selectedEvents,
      };
      const created = await api.createNotificationChannel(activeWorkspaceId, req);
      setChannels((prev) => [created, ...prev]);
      setShowCreateChannelModal(false);
      setNewChannelName("");
      setNewChannelUrl("");
      setSelectedEvents(ALL_NOTIFICATION_EVENTS.map((e) => e.id));
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create notification channel");
    } finally {
      setCreatingChannel(false);
    }
  };

  const handleDeleteChannel = async (channelId: string) => {
    if (!confirm("Are you sure you want to delete this notification channel?")) return;

    try {
      await api.deleteNotificationChannel(activeWorkspaceId, channelId);
      setChannels((prev) => prev.filter((c) => c.channel_id !== channelId));
      fetchWorkspaceDetails(activeWorkspaceId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete notification channel");
    }
  };

  const handleTestChannel = async (channelId: string) => {
    try {
      setTestingChannelId(channelId);
      setTestResult(null);
      setTestError(null);
      const res = await api.testNotificationChannel(
        activeWorkspaceId,
        channelId,
        "Notification channel test ping from Agent Evaluation Platform."
      );
      setTestResult(res);
      // Refresh delivery history
      const history = await api.listNotificationHistory(activeWorkspaceId).catch(() => []);
      setDeliveries(history);
    } catch (err) {
      setTestError(err instanceof Error ? err.message : "Test alert delivery failed");
    } finally {
      setTestingChannelId(null);
    }
  };

  const toggleEventSelection = (eventId: NotificationEventType) => {
    setSelectedEvents((prev) =>
      prev.includes(eventId) ? prev.filter((id) => id !== eventId) : [...prev, eventId]
    );
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2500);
    } catch {
      // clipboard fallback
    }
  };

  const renderRoleBadge = (role: WorkspaceRole | ServiceAccountRole) => {
    switch (role) {
      case "ADMIN":
        return (
          <span className="rounded bg-purple-50 border border-purple-200 px-2 py-0.5 text-[10px] font-bold text-purple-700">
            ADMIN
          </span>
        );
      case "ENGINEER":
        return (
          <span className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
            ENGINEER
          </span>
        );
      case "VIEWER":
        return (
          <span className="rounded bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-700">
            VIEWER
          </span>
        );
    }
  };

  const renderChannelTypeBadge = (type: NotificationChannelType) => {
    switch (type) {
      case "TEAMS":
        return (
          <span className="rounded bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
            Microsoft Teams
          </span>
        );
      case "SLACK":
        return (
          <span className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
            Slack
          </span>
        );
      case "WEBHOOK":
        return (
          <span className="rounded bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800">
            Generic Webhook
          </span>
        );
    }
  };

  const activeWorkspace = workspaces.find((w) => w.workspace_id === activeWorkspaceId);

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
            Team & Organization Workspaces
          </h1>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">
            Manage multi-tenant workspace boundaries, role-based access control (RBAC), outbound alerting webhooks, and team audit trails.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="self-start rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition"
        >
          + Create Workspace
        </button>
      </div>

      {/* 2. Error State */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* 3. Loading State */}
      {loading && (
        <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
          <span className="text-xs font-mono text-slate-500 animate-pulse">
            Loading workspaces and memberships...
          </span>
        </div>
      )}

      {!loading && (
        <>
          {/* 4. Workspace Selection Grid */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Workspaces ({workspaces.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workspaces.map((ws) => {
                const isSelected = ws.workspace_id === activeWorkspaceId;
                return (
                  <div
                    key={ws.workspace_id}
                    onClick={() => setActiveWorkspaceId(ws.workspace_id)}
                    className={`cursor-pointer rounded-xl border p-4 space-y-3 transition flex flex-col justify-between shadow-sm ${
                      isSelected
                        ? "border-emerald-500 bg-emerald-50/25 ring-1 ring-emerald-400"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:shadow"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-bold text-slate-900 text-sm truncate">{ws.name}</h3>
                        {ws.is_default && (
                          <span className="rounded bg-purple-50 border border-purple-200 px-2 py-0.5 text-[10px] font-bold text-purple-700">
                            DEFAULT
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                        {ws.description || "No description provided."}
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] text-slate-500 font-mono">
                      <span>{ws.member_count} member{ws.member_count !== 1 ? "s" : ""}</span>
                      {!ws.is_default && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteWorkspace(ws.workspace_id);
                          }}
                          className="text-rose-600 hover:text-rose-700 font-semibold transition"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 5. Active Workspace Management View */}
          {activeWorkspace && (
            <div className="space-y-6 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-600">
                    Active Workspace
                  </span>
                  <h2 className="text-xl font-black text-slate-900">{activeWorkspace.name}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-slate-100 border border-slate-200 px-2.5 py-1 text-xs font-mono text-slate-700">
                    Slug: {activeWorkspace.slug}
                  </span>
                </div>
              </div>

              {/* Tabs Switcher */}
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("team")}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition ${
                    activeTab === "team"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  Team & Governance ({members.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("api_keys")}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5 ${
                    activeTab === "api_keys"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  API Keys & Service Accounts ({apiKeys.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("notifications")}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5 ${
                    activeTab === "notifications"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  Notifications & Alerting ({channels.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("otel")}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition flex items-center gap-1.5 ${
                    activeTab === "otel"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  OTEL Integrations
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("audit")}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition ${
                    activeTab === "audit"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  Audit Trail ({auditLogs.length})
                </button>
              </div>

              {/* Tab 1: Team & Governance View */}
              {activeTab === "team" && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 5a. Team Members & RBAC */}
                  <div
                    data-testid="members-section"
                    className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-sm flex flex-col justify-between"
                  >
                    <div className="space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Team Members ({members.length})
                        </h3>
                        <span className="text-[10px] text-slate-500 font-medium">RBAC Enabled</span>
                      </div>

                      {/* Member Roster List */}
                      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                        {members.length > 0 ? (
                          members.map((member) => (
                            <div
                              key={member.member_id}
                              className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition"
                            >
                              <div className="flex items-center gap-3">
                                <div className="h-7 w-7 rounded-full bg-slate-200 flex items-center justify-center font-bold text-xs text-slate-700">
                                  {member.user_email[0].toUpperCase()}
                                </div>
                                <div>
                                  <div className="font-semibold text-xs text-slate-900">
                                    {member.user_email}
                                  </div>
                                  <div className="text-[10px] text-slate-500">
                                    Joined {new Date(member.joined_at).toLocaleDateString()}
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                {renderRoleBadge(member.role)}
                                {member.role !== "ADMIN" && (
                                  <button
                                    onClick={() => handleRemoveMember(member.member_id)}
                                    className="text-slate-400 hover:text-rose-600 text-xs px-1"
                                    title="Remove member"
                                  >
                                    ✕
                                  </button>
                                )}
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="p-4 text-center text-slate-500 text-xs">
                            No members assigned yet.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Add Member Form */}
                    <form
                      onSubmit={handleAddMember}
                      className="border-t border-slate-100 pt-4 flex gap-2 items-center text-xs"
                    >
                      <input
                        type="email"
                        required
                        placeholder="engineer@example.com"
                        value={newMemberEmail}
                        onChange={(e) => setNewMemberEmail(e.target.value)}
                        className="flex-1 rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                      />
                      <select
                        value={newMemberRole}
                        onChange={(e) => setNewMemberRole(e.target.value as WorkspaceRole)}
                        className="rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                      >
                        <option value="VIEWER">VIEWER</option>
                        <option value="ENGINEER">ENGINEER</option>
                        <option value="ADMIN">ADMIN</option>
                      </select>
                      <button
                        type="submit"
                        disabled={addingMember}
                        className="rounded-lg bg-slate-900 px-3.5 py-2 font-bold text-white hover:bg-slate-800 disabled:opacity-50 transition shrink-0"
                      >
                        {addingMember ? "Adding..." : "Add"}
                      </button>
                    </form>
                  </div>

                  {/* 5b. Workspace Governance Audit Logs */}
                  <div
                    data-testid="audit-logs-section"
                    className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-sm"
                  >
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                        Workspace Activity Audit Trail
                      </h3>
                      <span className="text-[10px] text-slate-500 font-medium">Immutable Log</span>
                    </div>

                    <div className="space-y-2 max-h-96 overflow-y-auto pr-1 font-mono text-xs">
                      {auditLogs.length > 0 ? (
                        auditLogs.map((log) => (
                          <div
                            key={log.log_id}
                            className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 space-y-1"
                          >
                            <div className="flex justify-between items-center text-[11px]">
                              <span className="font-bold text-emerald-700">{log.action}</span>
                              <span className="text-slate-500 text-[10px]">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </span>
                            </div>
                            <p className="text-slate-700 text-[11px]">
                              Actor: <strong className="text-slate-900">{log.actor_email}</strong> · Type: {log.resource_type}
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="p-4 text-center text-slate-500 text-xs">
                          No recent activity recorded in this workspace.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: API Keys & Service Accounts View */}
              {activeTab === "api_keys" && (
                <div
                  data-testid="api-keys-section"
                  className="rounded-xl border border-slate-200 bg-white p-5 space-y-5 shadow-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Workspace API Keys & Service Accounts
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Scoped programmatic credentials for CI/CD pipelines (GitHub Actions, GitLab, Jenkins) to submit traces and evaluations.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowCreateKeyModal(true)}
                      className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition self-start"
                    >
                      + Generate API Key
                    </button>
                  </div>

                  {apiKeys.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center space-y-2">
                      <p className="text-xs font-semibold text-slate-700">No active API keys found</p>
                      <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                        Generate a workspace-scoped token to authenticate your CI/CD runner or backend agent runtime.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-slate-600">
                        <thead>
                          <tr className="border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                            <th className="py-2.5">Key Name</th>
                            <th className="py-2.5">Key ID / Prefix</th>
                            <th className="py-2.5">Role</th>
                            <th className="py-2.5">Status</th>
                            <th className="py-2.5">Created</th>
                            <th className="py-2.5">Expires</th>
                            <th className="py-2.5">Last Used</th>
                            <th className="py-2.5 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {apiKeys.map((key) => {
                            const isExpired = key.expires_at && new Date(key.expires_at) < new Date();
                            return (
                              <tr key={key.key_id} className="hover:bg-slate-50/75 transition">
                                <td className="py-3 font-semibold text-slate-900">{key.name}</td>
                                <td className="py-3 font-mono text-[11px] text-slate-700">
                                  <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-bold text-slate-800 border border-slate-200">
                                    {key.key_prefix ? `${key.key_prefix}••••••••` : `${key.key_id.slice(0, 8)}...`}
                                  </code>
                                </td>
                                <td className="py-3">{renderRoleBadge(key.role)}</td>
                                <td className="py-3">
                                  {!key.is_active ? (
                                    <span className="rounded bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                                      REVOKED
                                    </span>
                                  ) : isExpired ? (
                                    <span className="rounded bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                                      EXPIRED
                                    </span>
                                  ) : (
                                    <span className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                      ACTIVE
                                    </span>
                                  )}
                                </td>
                                <td className="py-3 text-[11px] text-slate-500">
                                  {new Date(key.created_at).toLocaleDateString()}
                                </td>
                                <td className="py-3 text-[11px] text-slate-500">
                                  {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : "Never"}
                                </td>
                                <td className="py-3 text-[11px]">
                                  {key.last_used_at ? (
                                    <span className="text-slate-700 font-medium">
                                      {new Date(key.last_used_at).toLocaleDateString()}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400">Never</span>
                                  )}
                                </td>
                                <td className="py-3 text-right">
                                  {key.is_active && !isExpired ? (
                                    <button
                                      type="button"
                                      onClick={() => handleRevokeApiKey(key.key_id)}
                                      className="rounded border border-rose-200 bg-rose-50 px-2.5 py-1 text-[11px] font-bold text-rose-700 hover:bg-rose-100 transition shadow-2xs"
                                    >
                                      Revoke
                                    </button>
                                  ) : (
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">
                                      Revoked
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Notifications & Alerting Hub View */}
              {activeTab === "notifications" && (
                <div
                  data-testid="notifications-section"
                  className="space-y-6"
                >
                  {/* Test Feedback Alerts */}
                  {testResult && (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800 flex items-center justify-between shadow-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-600 font-bold">✓</span>
                        <div>
                          <strong className="font-semibold">Test Alert Dispatched:</strong> {testResult.message}
                          <span className="ml-2 font-mono text-[11px] text-emerald-700">
                            (HTTP {testResult.http_status ?? "200 OK"})
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => setTestResult(null)}
                        className="text-emerald-700 hover:text-emerald-900 font-bold ml-4"
                      >
                        ✕
                      </button>
                    </div>
                  )}

                  {testError && (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-center justify-between shadow-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-rose-600 font-bold">✕</span>
                        <div>
                          <strong className="font-semibold">Test Alert Failed:</strong> {testError}
                        </div>
                      </div>
                      <button
                        onClick={() => setTestError(null)}
                        className="text-rose-700 hover:text-rose-900 font-bold ml-4"
                      >
                        ✕
                      </button>
                    </div>
                  )}

                  {/* Channel Management Card */}
                  <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-5 shadow-sm">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Configured Webhook Channels ({channels.length})
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Notification destinations dispatching governance, evaluation, regression, and security alerts.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowCreateChannelModal(true)}
                        className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition self-start"
                      >
                        + Add Notification Channel
                      </button>
                    </div>

                    {channels.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center space-y-2">
                        <p className="text-xs font-semibold text-slate-700">No notification channels configured</p>
                        <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                          Connect a Microsoft Teams incoming webhook, Slack webhook, or generic endpoint to receive live alerts.
                        </p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {channels.map((ch) => (
                          <div
                            key={ch.channel_id}
                            className="rounded-xl border border-slate-200 bg-slate-50/40 p-4 space-y-3.5 flex flex-col justify-between hover:border-slate-300 transition"
                          >
                            <div className="space-y-2">
                              <div className="flex items-center justify-between gap-2">
                                <h4 className="font-bold text-sm text-slate-900 truncate">{ch.name}</h4>
                                {renderChannelTypeBadge(ch.channel_type)}
                              </div>

                              <div className="space-y-1">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                  Webhook Endpoint
                                </span>
                                <div className="rounded bg-white border border-slate-200 px-2 py-1 font-mono text-[11px] text-slate-700 truncate">
                                  {ch.webhook_url_masked}
                                </div>
                              </div>

                              <div className="space-y-1 pt-1">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                  Subscribed Events ({ch.events.length})
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  {ch.events.map((evt) => (
                                    <span
                                      key={evt}
                                      className="rounded bg-slate-100 border border-slate-200 px-1.5 py-0.5 text-[9px] font-mono font-medium text-slate-700"
                                    >
                                      {evt}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center justify-between pt-3 border-t border-slate-200/60">
                              <span className="text-[10px] text-slate-500">
                                Created {new Date(ch.created_at).toLocaleDateString()}
                              </span>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  disabled={testingChannelId === ch.channel_id}
                                  onClick={() => handleTestChannel(ch.channel_id)}
                                  className="rounded border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700 hover:bg-blue-100 transition shadow-2xs disabled:opacity-50"
                                >
                                  {testingChannelId === ch.channel_id ? "Sending..." : "Send Test Alert"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteChannel(ch.channel_id)}
                                  className="rounded border border-rose-200 bg-rose-50 px-2.5 py-1 text-[11px] font-bold text-rose-700 hover:bg-rose-100 transition shadow-2xs"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Delivery History & Diagnostics Table */}
                  <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                          Delivery History & Diagnostics ({deliveries.length})
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Audit trail of recent outbound alert attempts, delivery verdicts, and failure diagnostics.
                        </p>
                      </div>
                      <span className="text-[10px] text-slate-500 font-medium">Automatic Retry (3x Backoff)</span>
                    </div>

                    {deliveries.length === 0 ? (
                      <div className="p-8 text-center text-slate-500 text-xs">
                        No notification dispatches recorded yet for this workspace.
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-600">
                          <thead>
                            <tr className="border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                              <th className="py-2.5">Status</th>
                              <th className="py-2.5">Event Type</th>
                              <th className="py-2.5">HTTP Code</th>
                              <th className="py-2.5">Diagnostics / Details</th>
                              <th className="py-2.5 text-right">Timestamp</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {deliveries.map((del) => (
                              <tr key={del.delivery_id} className="hover:bg-slate-50/75 transition">
                                <td className="py-2.5">
                                  {del.status === "DELIVERED" ? (
                                    <span className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                      DELIVERED
                                    </span>
                                  ) : del.status === "FAILED" ? (
                                    <span className="rounded bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                                      FAILED
                                    </span>
                                  ) : (
                                    <span className="rounded bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                                      PENDING
                                    </span>
                                  )}
                                </td>
                                <td className="py-2.5 font-mono text-[11px] font-semibold text-slate-800">
                                  {del.event_type}
                                </td>
                                <td className="py-2.5 font-mono text-[11px]">
                                  {del.http_status ? (
                                    <span className={del.http_status < 400 ? "text-emerald-700 font-bold" : "text-rose-700 font-bold"}>
                                      {del.http_status}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400">—</span>
                                  )}
                                </td>
                                <td className="py-2.5 text-[11px] max-w-md truncate">
                                  {del.error_message ? (
                                    <span className="text-rose-700 font-mono">{del.error_message}</span>
                                  ) : (
                                    <span className="text-slate-500">Webhook delivery succeeded</span>
                                  )}
                                </td>
                                <td className="py-2.5 text-right font-mono text-[10px] text-slate-500">
                                  {new Date(del.created_at).toLocaleString()}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 4: Dedicated Full Audit Trail View */}
              {activeTab === "audit" && (
                <div
                  data-testid="audit-logs-section"
                  className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 shadow-sm"
                >
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                        Workspace Activity Audit Trail ({auditLogs.length})
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Immutable audit log recording member changes, trace submissions, evaluations, API keys, and notification dispatches.
                      </p>
                    </div>
                    <span className="text-[10px] text-slate-500 font-medium">Immutable Log</span>
                  </div>

                  <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1 font-mono text-xs">
                    {auditLogs.length > 0 ? (
                      auditLogs.map((log) => (
                        <div
                          key={log.log_id}
                          className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 space-y-1.5"
                        >
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="font-bold text-emerald-700">{log.action}</span>
                            <span className="text-slate-500 text-[10px]">
                              {new Date(log.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-slate-700 text-[11px]">
                            Actor: <strong className="text-slate-900">{log.actor_email}</strong> · Resource: {log.resource_type} ({log.resource_id || "workspace"})
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="p-8 text-center text-slate-500 text-xs">
                        No recent activity recorded in this workspace.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 5: OpenTelemetry Collector Integrations View */}
              {activeTab === "otel" && (
                <div data-testid="otel-integrations-section" className="space-y-6">
                  {/* Connection Credentials & Endpoints */}
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-emerald-100 p-1 text-emerald-600">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                        </span>
                        <h3 className="text-base font-bold text-slate-900">
                          OpenTelemetry Native Collector Receiver
                        </h3>
                      </div>
                      <p className="text-slate-500 text-xs mt-1">
                        Stream traces directly from standard OpenTelemetry Collectors and agent SDKs into this workspace. Traces are automatically translated to Canonical Agent Trace Schema (CATS) and audited across 7 evaluation domains.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          OTLP/HTTP Endpoint
                        </span>
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-mono text-xs font-semibold text-slate-900 truncate">
                            /api/v1/otel/collector
                          </span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard("http://localhost:8000/api/v1/otel/collector")}
                            className="text-[11px] font-bold text-blue-600 hover:text-blue-700 transition"
                          >
                            Copy
                          </button>
                        </div>
                        <span className="text-[10px] text-slate-400 block">
                          Alias: <code className="text-slate-600">/v1/traces</code>
                        </span>
                      </div>

                      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          OTLP/gRPC Endpoint
                        </span>
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-mono text-xs font-semibold text-slate-900 truncate">
                            localhost:4317
                          </span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard("localhost:4317")}
                            className="text-[11px] font-bold text-blue-600 hover:text-blue-700 transition"
                          >
                            Copy
                          </button>
                        </div>
                        <span className="text-[10px] text-slate-400 block">
                          Service: <code className="text-slate-600">TraceService/Export</code>
                        </span>
                      </div>

                      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Workspace Binding
                        </span>
                        <span className="font-semibold text-xs text-slate-900 block truncate">
                          {activeWorkspace.name}
                        </span>
                        <span className="font-mono text-[10px] text-emerald-600 block truncate">
                          ID: {activeWorkspace.workspace_id}
                        </span>
                      </div>

                      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Rate Limiting & Gating
                        </span>
                        <span className="font-bold text-xs text-emerald-600 block">
                          120 req/min · 50 Concurrency
                        </span>
                        <span className="text-[10px] text-slate-400 block">
                          Payload cap: 15MB · Max 10k spans
                        </span>
                      </div>
                    </div>

                    {/* Authentication Guidance */}
                    <div className="rounded-lg border border-blue-100 bg-blue-50/50 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="space-y-0.5">
                        <span className="text-xs font-bold text-blue-900">
                          Authenticate Collector with Workspace API Key
                        </span>
                        <p className="text-[11px] text-blue-700">
                          Pass your workspace API key in HTTP header <code className="font-mono bg-blue-100/70 px-1 py-0.5 rounded text-blue-900">Authorization: Bearer &lt;key&gt;</code> or <code className="font-mono bg-blue-100/70 px-1 py-0.5 rounded text-blue-900">x-api-key: &lt;key&gt;</code>.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab("api_keys")}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 transition shrink-0 self-start sm:self-auto"
                      >
                        Manage API Keys
                      </button>
                    </div>
                  </div>

                  {/* Framework Integration Configurations */}
                  <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">
                          Framework & Collector Setup Snippets
                        </h4>
                        <p className="text-slate-500 text-xs">
                          Copy production configurations to stream agent traces directly into this evaluation workspace.
                        </p>
                      </div>
                      {copiedSnippet && (
                        <span className="rounded bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-xs font-bold text-emerald-700 animate-fade-in">
                          Copied to clipboard!
                        </span>
                      )}
                    </div>

                    {/* Framework Pills */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      {OTEL_FRAMEWORKS.map((fw) => {
                        const isSelected = selectedOtelFramework === fw.id;
                        return (
                          <button
                            key={fw.id}
                            type="button"
                            onClick={() => setSelectedOtelFramework(fw.id)}
                            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition flex items-center gap-1.5 ${
                              isSelected
                                ? "bg-slate-900 text-white shadow-xs"
                                : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
                            }`}
                          >
                            <span>{fw.name}</span>
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                                isSelected ? "bg-slate-800 text-slate-200" : "bg-slate-200 text-slate-600"
                              }`}
                            >
                              {fw.tag}
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Active Framework Snippet */}
                    {(() => {
                      const activeFw = OTEL_FRAMEWORKS.find((f) => f.id === selectedOtelFramework) || OTEL_FRAMEWORKS[0];
                      return (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-600">
                              {activeFw.description}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                copyToClipboard(activeFw.code);
                                setCopiedSnippet(activeFw.id);
                                setTimeout(() => setCopiedSnippet(null), 2500);
                              }}
                              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition flex items-center gap-1.5 shadow-xs"
                            >
                              <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                              {copiedSnippet === activeFw.id ? "Copied!" : "Copy Snippet"}
                            </button>
                          </div>

                          <div className="relative rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-200 overflow-x-auto">
                            <pre className="whitespace-pre">{activeFw.code}</pre>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* 6. Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">Create New Workspace</h3>
            <form onSubmit={handleCreateWorkspace} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Workspace Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Swarm Robotics Evaluation"
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Slug (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. swarm-robotics"
                  value={newWsSlug}
                  onChange={(e) => setNewWsSlug(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Description</label>
                <textarea
                  placeholder="Scope and purpose of this workspace..."
                  value={newWsDesc}
                  onChange={(e) => setNewWsDesc(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  rows={2}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingWs}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50 shadow-sm transition"
                >
                  {creatingWs ? "Creating..." : "Create Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. Create API Key Modal */}
      {showCreateKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Generate Workspace API Key</h3>
              <p className="text-xs text-slate-500 mt-1">
                Create a secret credential to authenticate headless services and CI/CD pipelines.
              </p>
            </div>

            <form onSubmit={handleCreateApiKey} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Key Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. GitHub Actions CI Runner"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Service Account Role</label>
                <select
                  value={newKeyRole}
                  onChange={(e) => setNewKeyRole(e.target.value as ServiceAccountRole)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="ENGINEER">ENGINEER (Ingest Traces, Run Evals & Regressions)</option>
                  <option value="VIEWER">VIEWER (Read-Only Scorecards & Benchmarks)</option>
                  <option value="ADMIN">ADMIN (Full Workspace Control)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Expiration Period</label>
                <select
                  value={newKeyExpiryDays ?? "never"}
                  onChange={(e) => {
                    const val = e.target.value;
                    setNewKeyExpiryDays(val === "never" ? null : parseInt(val, 10));
                  }}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="30">30 Days</option>
                  <option value="60">60 Days</option>
                  <option value="90">90 Days (Recommended)</option>
                  <option value="180">180 Days</option>
                  <option value="365">1 Year</option>
                  <option value="never">No Expiration</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateKeyModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingKey}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50 shadow-sm transition"
                >
                  {creatingKey ? "Generating..." : "Generate Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 8. Create Notification Channel Modal */}
      {showCreateChannelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Add Notification Channel</h3>
              <p className="text-xs text-slate-500 mt-1">
                Configure an incoming webhook to receive real-time governance, evaluation, and security alerts.
              </p>
            </div>

            <form onSubmit={handleCreateChannel} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Channel Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. #agent-governance-alerts"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Channel Platform / Format</label>
                <select
                  value={newChannelType}
                  onChange={(e) => setNewChannelType(e.target.value as NotificationChannelType)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="SLACK">Slack (Block Kit / Color Tiers)</option>
                  <option value="TEAMS">Microsoft Teams (MessageCard / Adaptive)</option>
                  <option value="WEBHOOK">Generic Outbound Webhook (JSON)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Webhook URL</label>
                <input
                  type="url"
                  required
                  placeholder={
                    newChannelType === "SLACK"
                      ? "https://hooks.slack.com/services/..."
                      : newChannelType === "TEAMS"
                      ? "https://example.webhook.office.com/webhookb2/..."
                      : "https://api.example.com/alerts"
                  }
                  value={newChannelUrl}
                  onChange={(e) => setNewChannelUrl(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 font-mono text-[11px] text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <label className="text-slate-700 font-medium">Subscribed Event Triggers</label>
                  <div className="flex items-center gap-2 text-[10px]">
                    <button
                      type="button"
                      onClick={() => setSelectedEvents(ALL_NOTIFICATION_EVENTS.map((e) => e.id))}
                      className="text-blue-600 hover:text-blue-800 font-semibold"
                    >
                      Select All
                    </button>
                    <span>·</span>
                    <button
                      type="button"
                      onClick={() => setSelectedEvents([])}
                      className="text-slate-500 hover:text-slate-700 font-semibold"
                    >
                      Clear All
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/60 p-2.5">
                  {ALL_NOTIFICATION_EVENTS.map((evt) => {
                    const isChecked = selectedEvents.includes(evt.id);
                    return (
                      <label
                        key={evt.id}
                        className="flex items-center gap-2 p-1.5 rounded hover:bg-white cursor-pointer transition select-none text-[11px]"
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleEventSelection(evt.id)}
                          className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <span className="text-slate-800 font-medium">{evt.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateChannelModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingChannel || selectedEvents.length === 0}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50 shadow-sm transition"
                >
                  {creatingChannel ? "Saving..." : "Save Channel"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 9. Copy Once Experience Modal */}
      {createdKeyResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 font-bold">
                ✓
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  API Key Generated Successfully
                </h3>
                <p className="text-xs text-slate-500">Key Name: {createdKeyResult.name}</p>
              </div>
            </div>

            {/* Amber warning callout */}
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <span>⚠️</span> Copy your secret API key now
              </p>
              <p className="text-[11px] text-amber-700 leading-relaxed">
                For security, this token is hashed with SHA-256 and{" "}
                <strong>will not be displayed again</strong>. Store it in your CI/CD secrets manager (e.g.
                GitHub Secrets).
              </p>
            </div>

            {/* Secret key box */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Secret Token
              </label>
              <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                <code className="flex-1 font-mono text-xs font-semibold text-slate-900 break-all select-all">
                  {createdKeyResult.raw_key}
                </code>
                <button
                  type="button"
                  onClick={() => copyToClipboard(createdKeyResult.raw_key)}
                  className="shrink-0 rounded-md bg-white border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-100 transition"
                >
                  {copiedKey ? "✓ Copied!" : "Copy"}
                </button>
              </div>
            </div>

            {/* Integration Quickstart */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                cURL Integration Example
              </label>
              <pre className="rounded-lg border border-slate-200 bg-slate-900 p-3 font-mono text-[11px] text-slate-200 overflow-x-auto">
{`curl -H "Authorization: Bearer ${createdKeyResult.raw_key}" \\
  http://localhost:8000/api/v1/auth/verify`}
              </pre>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setCreatedKeyResult(null)}
                className="rounded-lg bg-slate-900 px-5 py-2 text-xs font-bold text-white hover:bg-slate-800 shadow-sm transition"
              >
                I Have Saved My Secret Key
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
