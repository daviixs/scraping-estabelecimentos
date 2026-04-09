/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowClockwise,
  Checks,
  DownloadSimple,
  FunnelSimple,
  PauseCircle,
  PaperPlaneTilt,
  WarningCircle,
} from "@phosphor-icons/react";

import ScanCommander from "./ScanCommander";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";
import { cn } from "../lib/utils";

type TabKey = "estabelecimentos" | "mensagens";

type Estabelecimento = {
  id?: number;
  nome?: string;
  categoria?: string;
  cidade?: string;
  bairro?: string;
  telefone?: string;
  nota_media?: number;
  total_avaliacoes?: number;
  score_oportunidade?: number;
  prioridade_lead?: string;
  faixa_classificacao?: string;
  resumo_queixas?: string;
  fonte?: string;
  data_coleta?: string;
  link_origem?: string;
  aprovado_disparo?: number;
  status_whatsapp?: string;
};

type Resumo = {
  total: number;
  alta: number;
  media: number;
  baixa: number;
  aprovados: number;
  enviados_hoje: number;
  aguardando_envio: number;
  score_medio: number;
  ultima_coleta: string;
};

type QueueItem = {
  id: number;
  estabelecimento_id: number;
  nome?: string;
  categoria?: string;
  cidade?: string;
  telefone?: string;
  mensagem?: string;
  origem_disparo?: string;
  status?: string;
  tentativas?: number;
  data_agendamento?: string;
  data_envio?: string;
  erro_descricao?: string;
};

type DispatchLead = Estabelecimento & {
  dispatch_state?: string;
  queue_item_id?: number | null;
  queue_status?: string | null;
  queue_data_agendamento?: string | null;
  queue_origem_disparo?: string | null;
};

type MessageConfig = {
  modo_envio: "manual" | "automatico";
  atualizado_em?: string | null;
};

type SchedulerSnapshot = {
  running: boolean;
  paused: boolean;
  next_run_at?: string | null;
  sent_today: number;
  pending_items: number;
  daily_limit: number;
  window_label: string;
  heartbeat_seconds: number;
  last_error?: string | null;
  enqueued?: number;
};

const stagger = {
  hidden: { opacity: 0, y: 12 },
  show: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: index * 0.05, type: "spring", stiffness: 96, damping: 18 },
  }),
};

const classificationOptions = [
  { label: "Muito bom", value: "MUITO BOM" },
  { label: "Medio", value: "MEDIO" },
  { label: "Muito ruim", value: "MUITO RUIM" },
];

const priorityOptions = [
  { label: "Alta", value: "ALTA" },
  { label: "Media", value: "MEDIA" },
  { label: "Baixa", value: "BAIXA" },
];

const sourceOptions = [
  { label: "Google Maps", value: "google_maps" },
  { label: "Apontador", value: "apontador" },
  { label: "Manual", value: "manual" },
];

const orderOptions = [
  ["score_oportunidade", "Score de oportunidade"],
  ["nota_media", "Nota media"],
  ["total_avaliacoes", "Avaliacoes"],
  ["nome", "Nome"],
  ["categoria", "Categoria"],
  ["cidade", "Cidade"],
  ["prioridade_lead", "Prioridade"],
  ["status_whatsapp", "Status WhatsApp"],
] as const;

const statusOptions = [
  { label: "Todos", value: "all" },
  { label: "Pendente", value: "pendente" },
  { label: "Enviado", value: "enviado" },
  { label: "Sem WhatsApp", value: "sem_whatsapp" },
  { label: "Erro", value: "erro" },
];

const approvalOptions = [
  { label: "Todos", value: "all" },
  { label: "Aprovados", value: "approved" },
  { label: "Nao aprovados", value: "not_approved" },
];

const tonePanel: Record<"blush" | "sage" | "sky" | "sun", string> = {
  blush: "border-blush-200 bg-blush-50/80",
  sage: "border-sage-200 bg-sage-50/80",
  sky: "border-sky-200 bg-sky-50/80",
  sun: "border-sun-200 bg-sun-50/80",
};

const selectClassName =
  "h-11 w-full rounded-2xl border border-sand-200/90 bg-white/80 px-3.5 text-sm text-graphite outline-none transition focus:border-accent/40 focus:ring-2 focus:ring-accent/25";

function normalizeLabel(value?: string | null) {
  if (!value) return "--";
  return value
    .replace("M\u00c3\u0192\u00e2\u20ac\u00b0DIA", "MEDIA")
    .replace("M\u00c3\u2030DIA", "MEDIA")
    .replace("M\u00c9DIA", "MEDIA")
    .replace("M\u00c3\u0192\u00e2\u20ac\u00b0DIO", "MEDIO")
    .replace("M\u00c3\u2030DIO", "MEDIO")
    .replace("M\u00c9DIO", "MEDIO");
}

function formatDateTime(value?: string | null) {
  if (!value) return "--";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  const parts = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(parsed);
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${byType.day}/${byType.month}/${byType.year} ${byType.hour}:${byType.minute}`;
}

function formatSource(value?: string | null) {
  if (!value) return "--";
  const labels: Record<string, string> = {
    google_maps: "Google Maps",
    apontador: "Apontador",
    manual: "Manual",
  };
  return labels[value] || value.replaceAll("_", " ");
}

function formatLocation(cidade?: string, bairro?: string) {
  if (cidade && bairro) return `${cidade} / ${bairro}`;
  return cidade || bairro || "--";
}

function scoreTone(score?: number) {
  if (score === undefined || score === null) return "bg-sand-300";
  if (score >= 60) return "bg-accent";
  if (score >= 35) return "bg-sun-500";
  return "bg-blush-500";
}

function statusTone(status?: string | null) {
  if (status === "enviado") return "border-sage-200 bg-sage-50 text-sage-700";
  if (status === "sem_whatsapp") return "border-sun-200 bg-sun-50 text-sun-700";
  if (status === "erro") return "border-blush-200 bg-blush-50 text-blush-700";
  return "border-sky-200 bg-sky-50 text-sky-700";
}

function approvalTone(isApproved?: number | null) {
  return isApproved
    ? "border-sage-200 bg-sage-50 text-sage-700"
    : "border-sand-200 bg-sand-50 text-gray-600";
}

function dispatchStateTone(state?: string | null) {
  if (state === "na_fila") return "border-sky-200 bg-sky-50 text-sky-700";
  if (state === "aprovado") return "border-sage-200 bg-sage-50 text-sage-700";
  if (state === "erro") return "border-blush-200 bg-blush-50 text-blush-700";
  if (state === "sem_whatsapp") return "border-sun-200 bg-sun-50 text-sun-700";
  if (state === "enviado") return "border-graphite/15 bg-graphite/5 text-graphite";
  return "border-sand-200 bg-sand-50 text-gray-600";
}

function formatDispatchState(state?: string | null) {
  if (state === "na_fila") return "Na fila";
  if (state === "aprovado") return "Aprovado";
  if (state === "erro") return "Erro";
  if (state === "sem_whatsapp") return "Sem WhatsApp";
  if (state === "enviado") return "Enviado";
  return "Disponivel";
}

function formatDispatchOrigin(origin?: string | null) {
  if (origin === "automatico") return "Automatico";
  return "Manual";
}

function FilterToggle({
  label,
  checked,
  onChange,
  tone,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
  tone: keyof typeof tonePanel;
}) {
  return (
    <label
      className={cn(
        "flex items-center justify-between gap-3 rounded-2xl border px-3 py-3 text-sm transition",
        checked ? tonePanel[tone] : "border-sand-200/90 bg-white/70 hover:bg-white"
      )}
    >
      <span className="min-w-0 break-words font-medium text-graphite">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-4 w-4 rounded border-sand-300 bg-white text-accent focus:ring-2 focus:ring-accent/30"
      />
    </label>
  );
}

function MetaBlock({
  label,
  value,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  tone: keyof typeof tonePanel;
}) {
  return (
    <div className={cn("rounded-2xl border px-4 py-3", tonePanel[tone])}>
      <p className="text-[11px] uppercase tracking-[0.22em] text-gray-500">{label}</p>
      <div className="mt-2 break-words text-sm font-medium text-graphite">{value}</div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  helper,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  helper: React.ReactNode;
  tone: keyof typeof tonePanel;
}) {
  return (
    <Card className={cn("h-full overflow-hidden", tonePanel[tone])}>
      <CardHeader className="gap-3">
        <span
          className={cn(
            "h-1 w-12 rounded-full",
            tone === "blush"
              ? "bg-accent/80"
              : tone === "sky"
                ? "bg-sky-500"
                : tone === "sage"
                  ? "bg-sage-500"
                  : "bg-sun-500"
          )}
        />
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.24em] text-gray-500">{label}</p>
          <div className="text-3xl font-semibold tracking-tight text-graphite">{value}</div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 text-sm text-gray-600">{helper}</CardContent>
    </Card>
  );
}

function requestJson(url: string, init?: RequestInit) {
  return fetch(url, init).then(async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || "Falha ao processar a requisicao.");
    }
    return payload;
  });
}

export default function DashboardApp() {
  const [activeTab, setActiveTab] = useState<TabKey>("estabelecimentos");
  const [data, setData] = useState<Estabelecimento[]>([]);
  const [dispatchLeads, setDispatchLeads] = useState<DispatchLead[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerSnapshot | null>(null);
  const [messageConfig, setMessageConfig] = useState<MessageConfig | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [orderBy, setOrderBy] = useState("score_oportunidade");
  const [orderDir, setOrderDir] = useState<"asc" | "desc">("desc");
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [cidades, setCidades] = useState<string[]>([]);
  const [categorias, setCategorias] = useState<string[]>([]);
  const [loadingTable, setLoadingTable] = useState(true);
  const [loadingKpi, setLoadingKpi] = useState(true);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDispatchLeads, setLoadingDispatchLeads] = useState(true);
  const [busyApproval, setBusyApproval] = useState(false);
  const [busyDispatch, setBusyDispatch] = useState(false);
  const [busyModeChange, setBusyModeChange] = useState(false);
  const [busyQueueSelection, setBusyQueueSelection] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedDispatchIds, setSelectedDispatchIds] = useState<number[]>([]);
  const [dispatchSearch, setDispatchSearch] = useState("");
  const [dispatchStateFilter, setDispatchStateFilter] = useState("all");
  const [filtros, setFiltros] = useState({
    classificacao: [] as string[],
    prioridade: [] as string[],
    fonte: [] as string[],
    cidade: "",
    categoria: "",
    score_min: 0,
    status_whatsapp: "all",
    aprovado_disparo: "all",
  });

  const queryString = (params: Record<string, any>) =>
    Object.entries(params)
      .filter(
        ([_, value]) =>
          value !== null &&
          value !== undefined &&
          value !== "" &&
          value !== "all" &&
          (!Array.isArray(value) || value.length > 0)
      )
      .map(([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(Array.isArray(value) ? value.join(",") : value)}`
      )
      .join("&");

  const fetchResumo = async () => {
    setLoadingKpi(true);
    try {
      const payload = await requestJson("/api/resumo");
      setResumo(payload);
    } finally {
      setLoadingKpi(false);
    }
  };

  const fetchFiltros = async () => {
    const [cidadesResponse, categoriasResponse] = await Promise.all([
      requestJson("/api/cidades"),
      requestJson("/api/categorias"),
    ]);
    setCidades(cidadesResponse);
    setCategorias(categoriasResponse);
  };

  const fetchData = async () => {
    setLoadingTable(true);
    setError(null);
    try {
      const query = queryString({
        classificacao: filtros.classificacao,
        prioridade: filtros.prioridade,
        fonte: filtros.fonte,
        cidade: filtros.cidade,
        categoria: filtros.categoria,
        score_min: filtros.score_min,
        status_whatsapp: filtros.status_whatsapp,
        aprovado_disparo: filtros.aprovado_disparo,
        page,
        per_page: perPage,
        order_by: orderBy,
        order_dir: orderDir,
      });
      const payload = await requestJson(`/api/estabelecimentos?${query}`);
      setData(payload.data);
      setPages(payload.pages);
      setTotal(payload.total);
    } catch (fetchError: any) {
      setError(fetchError.message || "Erro ao carregar estabelecimentos.");
      setData([]);
    } finally {
      setLoadingTable(false);
    }
  };

  const fetchMessagesData = async () => {
    setLoadingQueue(true);
    setMessagesError(null);
    try {
      const [queuePayload, statusPayload, configPayload] = await Promise.all([
        requestJson("/api/fila-disparos"),
        requestJson("/api/disparo/status"),
        requestJson("/api/mensagens/config"),
      ]);
      setQueue(queuePayload.data || []);
      setSchedulerStatus(statusPayload.scheduler || null);
      setMessageConfig(configPayload.config || null);
    } catch (fetchError: any) {
      setMessagesError(fetchError.message || "Erro ao carregar painel de mensagens.");
    } finally {
      setLoadingQueue(false);
    }
  };

  const fetchDispatchLeads = async () => {
    setLoadingDispatchLeads(true);
    setMessagesError(null);
    try {
      const query = queryString({
        q: dispatchSearch,
        limit: 72,
      });
      const payload = await requestJson(`/api/mensagens/elegiveis?${query}`);
      setDispatchLeads(payload.data || []);
    } catch (fetchError: any) {
      setMessagesError(fetchError.message || "Erro ao carregar leads para disparo.");
      setDispatchLeads([]);
    } finally {
      setLoadingDispatchLeads(false);
    }
  };

  const refreshAll = async () => {
    await Promise.all([fetchResumo(), fetchData(), fetchMessagesData(), fetchDispatchLeads()]);
  };

  useEffect(() => {
    fetchResumo().catch(() => null);
    fetchFiltros().catch(() => null);
    fetchMessagesData().catch(() => null);
    fetchDispatchLeads().catch(() => null);
  }, []);

  useEffect(() => {
    fetchData().catch(() => null);
  }, [page, perPage, orderBy, orderDir, filtros]);

  useEffect(() => {
    setSelectedIds((current) =>
      current.filter((id) => data.some((row) => row.id === id))
    );
  }, [data]);

  useEffect(() => {
    fetchDispatchLeads().catch(() => null);
  }, [dispatchSearch]);

  useEffect(() => {
    setSelectedDispatchIds((current) =>
      current.filter((id) => dispatchLeads.some((row) => row.id === id))
    );
  }, [dispatchLeads]);

  useEffect(() => {
    const shouldPoll = activeTab === "mensagens" || Boolean(schedulerStatus?.running);
    if (!shouldPoll) return;
    const interval = window.setInterval(() => {
      fetchMessagesData().catch(() => null);
      fetchDispatchLeads().catch(() => null);
      fetchResumo().catch(() => null);
      fetchData().catch(() => null);
    }, 10000);
    return () => window.clearInterval(interval);
  }, [activeTab, schedulerStatus?.running]);

  const totalPages = Math.max(pages, 1);
  const pagesArray = useMemo(() => {
    const items = [];
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + 4);
    for (let current = start; current <= end; current += 1) items.push(current);
    return items;
  }, [page, totalPages]);

  const rangeStart = total === 0 ? 0 : (page - 1) * perPage + 1;
  const rangeEnd = total === 0 ? 0 : Math.min(page * perPage, total);
  const visibleIds = data
    .map((row) => row.id)
    .filter((value): value is number => typeof value === "number");
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));
  const filteredDispatchLeads = dispatchLeads.filter((row) =>
    dispatchStateFilter === "all" ? true : row.dispatch_state === dispatchStateFilter
  );
  const visibleDispatchIds = filteredDispatchLeads
    .map((row) => row.id)
    .filter((value): value is number => typeof value === "number");
  const allDispatchVisibleSelected =
    visibleDispatchIds.length > 0 &&
    visibleDispatchIds.every((id) => selectedDispatchIds.includes(id));

  const toggleArray = (field: "classificacao" | "prioridade" | "fonte", value: string) => {
    setFiltros((prev) => {
      const exists = prev[field].includes(value);
      return {
        ...prev,
        [field]: exists
          ? prev[field].filter((item) => item !== value)
          : [...prev[field], value],
      };
    });
    setPage(1);
  };

  const toggleSelection = (id?: number) => {
    if (!id) return;
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleVisibleSelection = () => {
    setSelectedIds((prev) => {
      if (allVisibleSelected) {
        return prev.filter((id) => !visibleIds.includes(id));
      }
      return Array.from(new Set([...prev, ...visibleIds]));
    });
  };

  const toggleDispatchSelection = (id?: number) => {
    if (!id) return;
    setSelectedDispatchIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleVisibleDispatchSelection = () => {
    setSelectedDispatchIds((prev) => {
      if (allDispatchVisibleSelected) {
        return prev.filter((id) => !visibleDispatchIds.includes(id));
      }
      return Array.from(new Set([...prev, ...visibleDispatchIds]));
    });
  };

  const handleApproval = async (approved: boolean, ids: number[] = selectedIds) => {
    if (!ids.length) return;
    setBusyApproval(true);
    try {
      await requestJson(approved ? "/api/aprovar" : "/api/remover-aprovacao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      if (ids === selectedIds) {
        setSelectedIds([]);
      }
      if (ids === selectedDispatchIds) {
        setSelectedDispatchIds([]);
      }
      await Promise.all([fetchData(), fetchResumo(), fetchMessagesData(), fetchDispatchLeads()]);
    } catch (approvalError: any) {
      const message = approvalError.message || "Falha ao atualizar aprovacoes.";
      setError(message);
      setMessagesError(message);
    } finally {
      setBusyApproval(false);
    }
  };

  const handleMessageModeChange = async (modo_envio: "manual" | "automatico") => {
    setBusyModeChange(true);
    setMessagesError(null);
    try {
      const payload = await requestJson("/api/mensagens/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modo_envio }),
      });
      setMessageConfig(payload.config || null);
      await Promise.all([fetchMessagesData(), fetchDispatchLeads()]);
    } catch (configError: any) {
      setMessagesError(configError.message || "Falha ao atualizar o modo de envio.");
    } finally {
      setBusyModeChange(false);
    }
  };

  const handleQueueSelection = async () => {
    if (!selectedDispatchIds.length) return;
    setBusyQueueSelection(true);
    setMessagesError(null);
    try {
      await requestJson("/api/disparo/enfileirar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: selectedDispatchIds }),
      });
      setSelectedDispatchIds([]);
      await Promise.all([fetchMessagesData(), fetchResumo(), fetchData(), fetchDispatchLeads()]);
    } catch (queueError: any) {
      setMessagesError(queueError.message || "Falha ao adicionar selecionados a fila.");
    } finally {
      setBusyQueueSelection(false);
    }
  };

  const handleDispatchAction = async (path: "/api/disparo/iniciar" | "/api/disparo/pausar") => {
    setBusyDispatch(true);
    try {
      const payload = await requestJson(path, { method: "POST" });
      setSchedulerStatus(payload.scheduler || null);
      await Promise.all([fetchMessagesData(), fetchResumo(), fetchData(), fetchDispatchLeads()]);
    } catch (dispatchError: any) {
      setMessagesError(dispatchError.message || "Falha ao operar o scheduler.");
    } finally {
      setBusyDispatch(false);
    }
  };

  const exportQuery = queryString({
    classificacao: filtros.classificacao,
    prioridade: filtros.prioridade,
    fonte: filtros.fonte,
    cidade: filtros.cidade,
    categoria: filtros.categoria,
    score_min: filtros.score_min,
    status_whatsapp: filtros.status_whatsapp,
    aprovado_disparo: filtros.aprovado_disparo,
  });

  const renderEstablishments = () => (
    <div className="space-y-4">
      <ScanCommander onFinished={() => refreshAll().catch(() => null)} />

      <div className="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
        <motion.aside
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0, transition: { type: "spring", stiffness: 110, damping: 18 } }}
          className="space-y-4"
        >
          <Card className="overflow-hidden border-sand-200/90 bg-shell/90">
            <CardHeader className="border-b border-sand-200/80 bg-[linear-gradient(180deg,rgba(245,228,230,0.8),rgba(252,248,243,0.45))]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Filtros</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Refinar a base</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">
                    Prioridade, aprovacao, status WhatsApp e score na mesma superficie.
                  </p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-blush-200 bg-blush-50 text-accent">
                  <FunnelSimple size={18} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5 pt-5">
              <div className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Classificacao</p>
                  <p className="mt-1 text-sm text-gray-600">Leitura da reputacao atual.</p>
                </div>
                <div className="space-y-2">
                  {classificationOptions.map((item) => (
                    <FilterToggle
                      key={item.value}
                      label={item.label}
                      checked={filtros.classificacao.includes(item.value)}
                      onChange={() => toggleArray("classificacao", item.value)}
                      tone="sky"
                    />
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Prioridade</p>
                  <p className="mt-1 text-sm text-gray-600">Calor comercial da oportunidade.</p>
                </div>
                <div className="space-y-2">
                  {priorityOptions.map((item) => (
                    <FilterToggle
                      key={item.value}
                      label={item.label}
                      checked={filtros.prioridade.includes(item.value)}
                      onChange={() => toggleArray("prioridade", item.value)}
                      tone="blush"
                    />
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Fonte</p>
                  <p className="mt-1 text-sm text-gray-600">Origem da coleta armazenada na base.</p>
                </div>
                <div className="space-y-2">
                  {sourceOptions.map((item) => (
                    <FilterToggle
                      key={item.value}
                      label={item.label}
                      checked={filtros.fonte.includes(item.value)}
                      onChange={() => toggleArray("fonte", item.value)}
                      tone="sage"
                    />
                  ))}
                </div>
              </div>

              <div className="grid gap-4">
                <label className="space-y-2">
                  <span className="block text-xs uppercase tracking-[0.22em] text-gray-500">Cidade</span>
                  <select
                    className={selectClassName}
                    value={filtros.cidade}
                    onChange={(event) => {
                      setFiltros((prev) => ({ ...prev, cidade: event.target.value }));
                      setPage(1);
                    }}
                  >
                    <option value="">Todas</option>
                    {cidades.map((cidade) => (
                      <option key={cidade} value={cidade}>
                        {cidade}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="block text-xs uppercase tracking-[0.22em] text-gray-500">Categoria</span>
                  <select
                    className={selectClassName}
                    value={filtros.categoria}
                    onChange={(event) => {
                      setFiltros((prev) => ({ ...prev, categoria: event.target.value }));
                      setPage(1);
                    }}
                  >
                    <option value="">Todas</option>
                    {categorias.map((categoria) => (
                      <option key={categoria} value={categoria}>
                        {categoria}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="block text-xs uppercase tracking-[0.22em] text-gray-500">Aprovacao</span>
                  <select
                    className={selectClassName}
                    value={filtros.aprovado_disparo}
                    onChange={(event) => {
                      setFiltros((prev) => ({ ...prev, aprovado_disparo: event.target.value }));
                      setPage(1);
                    }}
                  >
                    {approvalOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="block text-xs uppercase tracking-[0.22em] text-gray-500">Status WhatsApp</span>
                  <select
                    className={selectClassName}
                    value={filtros.status_whatsapp}
                    onChange={(event) => {
                      setFiltros((prev) => ({ ...prev, status_whatsapp: event.target.value }));
                      setPage(1);
                    }}
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="rounded-2xl border border-sand-200/90 bg-white/65 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Score minimo</p>
                    <p className="mt-1 text-sm text-gray-600">Filtra a base por potencial comercial.</p>
                  </div>
                  <span className="rounded-full border border-blush-200 bg-blush-50 px-3 py-1 text-sm font-semibold text-accent">
                    {filtros.score_min}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={filtros.score_min}
                  onChange={(event) => {
                    setFiltros((prev) => ({ ...prev, score_min: Number(event.target.value) }));
                    setPage(1);
                  }}
                  className="mt-4 w-full accent-accent"
                />
              </div>
            </CardContent>
          </Card>
        </motion.aside>

        <motion.section
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0, transition: { type: "spring", stiffness: 110, damping: 18 } }}
          className="min-w-0"
        >
          <Card className="overflow-hidden border-sand-200/90 bg-shell/85">
            <CardHeader className="border-b border-sand-200/80 bg-white/45">
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px_auto] xl:items-end">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Resultados</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Base priorizada</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">
                    Mostrando {rangeStart}-{rangeEnd} de {total} registros com aprovacao e status visiveis.
                  </p>
                </div>

                <label className="space-y-2">
                  <span className="block text-xs uppercase tracking-[0.22em] text-gray-500">Ordenar por</span>
                  <select
                    className={selectClassName}
                    value={orderBy}
                    onChange={(event) => {
                      setOrderBy(event.target.value);
                      setPage(1);
                    }}
                  >
                    {orderOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <Button
                    variant="outline"
                    onClick={() => setOrderDir((current) => (current === "asc" ? "desc" : "asc"))}
                    className="gap-2"
                  >
                    <ArrowClockwise size={16} />
                    {orderDir === "asc" ? "Crescente" : "Decrescente"}
                  </Button>
                  <div className="flex items-center gap-3 rounded-2xl border border-sand-200 bg-white/70 px-3 py-2.5">
                    <span className="text-xs uppercase tracking-[0.2em] text-gray-500">Por pagina</span>
                    <Input
                      type="number"
                      min={5}
                      max={100}
                      value={perPage}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        if (Number.isNaN(nextValue)) return;
                        setPerPage(Math.max(5, Math.min(100, nextValue)));
                        setPage(1);
                      }}
                      className="h-9 w-20 bg-white"
                    />
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-5">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sand-200/80 bg-white/70 px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full border border-sand-200 bg-sand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-gray-600">
                    {selectedIds.length} selecionados
                  </span>
                  <Button variant="ghost" size="sm" onClick={toggleVisibleSelection}>
                    {allVisibleSelected ? "Limpar visiveis" : "Selecionar visiveis"}
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleApproval(true).catch(() => null)}
                    disabled={!selectedIds.length || busyApproval}
                    className="gap-2"
                  >
                    <Checks size={16} />
                    Aprovar selecionados
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleApproval(false).catch(() => null)}
                    disabled={!selectedIds.length || busyApproval}
                    className="gap-2"
                  >
                    <PauseCircle size={16} />
                    Remover aprovacao
                  </Button>
                </div>
              </div>

              {loadingTable && (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div
                      key={index}
                      className="rounded-[1.55rem] border border-sand-200/90 bg-white/75 p-5"
                    >
                      <Skeleton className="h-7 w-2/5" />
                      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
                        <Skeleton className="h-28" />
                        <div className="grid gap-3 sm:grid-cols-2">
                          <Skeleton className="h-20" />
                          <Skeleton className="h-20" />
                          <Skeleton className="h-20" />
                          <Skeleton className="h-20" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!loadingTable && data.length === 0 && (
                <div className="rounded-[1.55rem] border border-sand-200/90 bg-white/80 px-6 py-14 text-center">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Lista vazia</p>
                  <h3 className="mt-3 text-2xl font-semibold tracking-tight text-graphite">
                    Nenhum estabelecimento encontrado
                  </h3>
                  <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
                    {error || "Ajuste os filtros ou execute uma nova varredura para preencher a base novamente."}
                  </p>
                </div>
              )}

              <AnimatePresence>
                {!loadingTable &&
                  data.map((row, index) => {
                    const score = Math.min(Math.max(row.score_oportunidade || 0, 0), 100);
                    const note =
                      row.nota_media !== undefined && row.nota_media !== null
                        ? row.nota_media.toFixed(1)
                        : "--";
                    const selected = Boolean(row.id && selectedIds.includes(row.id));
                    return (
                      <motion.article
                        key={`${row.id || row.nome || "row"}-${index}`}
                        layout
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -6 }}
                        transition={{
                          type: "spring",
                          stiffness: 92,
                          damping: 18,
                          delay: index * 0.02,
                        }}
                        className={cn(
                          "overflow-hidden rounded-[1.55rem] border bg-white/80 p-5 shadow-diffuse",
                          selected ? "border-accent/50 ring-2 ring-accent/10" : "border-sand-200/90"
                        )}
                      >
                        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_290px]">
                          <div className="min-w-0 space-y-4">
                            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                              <div className="min-w-0 space-y-3">
                                <div className="flex flex-wrap items-center gap-2">
                                  <label className="inline-flex items-center gap-2 rounded-full border border-sand-200 bg-sand-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-600">
                                    <input
                                      type="checkbox"
                                      checked={selected}
                                      onChange={() => toggleSelection(row.id)}
                                      className="h-4 w-4 rounded border-sand-300 text-accent focus:ring-accent/30"
                                    />
                                    Selecionar
                                  </label>
                                  <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                                    {formatSource(row.fonte)}
                                  </span>
                                  {row.categoria && (
                                    <span className="rounded-full border border-sand-200 bg-sand-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-600">
                                      {row.categoria}
                                    </span>
                                  )}
                                </div>
                                {row.link_origem ? (
                                  <a
                                    href={row.link_origem}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="block break-words text-2xl font-semibold tracking-tight text-graphite transition hover:text-accent"
                                  >
                                    {row.nome || "Estabelecimento sem nome"}
                                  </a>
                                ) : (
                                  <p className="break-words text-2xl font-semibold tracking-tight text-graphite">
                                    {row.nome || "Estabelecimento sem nome"}
                                  </p>
                                )}
                                <p className="text-sm text-gray-600">{formatLocation(row.cidade, row.bairro)}</p>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                <Badge label={normalizeLabel(row.prioridade_lead)} />
                                <span
                                  className={cn(
                                    "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                                    statusTone(row.status_whatsapp)
                                  )}
                                >
                                  {row.status_whatsapp || "pendente"}
                                </span>
                                <span
                                  className={cn(
                                    "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                                    approvalTone(row.aprovado_disparo)
                                  )}
                                >
                                  {row.aprovado_disparo ? "Aprovado" : "Nao aprovado"}
                                </span>
                              </div>
                            </div>

                            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
                              <MetaBlock
                                label="Queixas principais"
                                value={row.resumo_queixas || "Sem observacoes registradas."}
                                tone="blush"
                              />
                              <div className="grid gap-3 sm:grid-cols-2">
                                <MetaBlock
                                  label="Cidade / Bairro"
                                  value={formatLocation(row.cidade, row.bairro)}
                                  tone="sky"
                                />
                                <MetaBlock label="Coleta" value={formatDateTime(row.data_coleta)} tone="sun" />
                                <MetaBlock label="Telefone" value={row.telefone || "--"} tone="sage" />
                                <MetaBlock
                                  label="Classificacao"
                                  value={normalizeLabel(row.faixa_classificacao)}
                                  tone="sky"
                                />
                              </div>
                            </div>
                          </div>

                          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                            <div className="rounded-2xl border border-sand-200 bg-shell/90 p-4">
                              <p className="text-[11px] uppercase tracking-[0.22em] text-gray-500">
                                Score de oportunidade
                              </p>
                              <div className="mt-3 flex items-end justify-between gap-3">
                                <span className="text-3xl font-semibold tracking-tight text-graphite">
                                  {score.toFixed(1)}
                                </span>
                                <span className="font-mono text-xs text-gray-500">0-100</span>
                              </div>
                              <div className="mt-3 h-2 overflow-hidden rounded-full bg-sand-200">
                                <motion.div
                                  className={cn("h-full", scoreTone(score))}
                                  initial={{ width: 0 }}
                                  animate={{ width: `${score}%` }}
                                  transition={{ type: "spring", stiffness: 96, damping: 16 }}
                                />
                              </div>
                            </div>
                            <div className="rounded-2xl border border-sage-200 bg-sage-50/80 p-4">
                              <p className="text-[11px] uppercase tracking-[0.22em] text-gray-500">Nota media</p>
                              <div className="mt-3 text-3xl font-semibold tracking-tight text-graphite">
                                {note}
                              </div>
                              <p className="mt-2 text-sm text-sage-700">
                                {row.nota_media && row.nota_media >= 4.6
                                  ? "Recepcao forte"
                                  : "Pede leitura comercial"}
                              </p>
                            </div>
                            <div className="rounded-2xl border border-sky-200 bg-sky-50/80 p-4">
                              <p className="text-[11px] uppercase tracking-[0.22em] text-gray-500">
                                Avaliacoes
                              </p>
                              <div className="mt-3 text-3xl font-semibold tracking-tight text-graphite">
                                {row.total_avaliacoes ?? "--"}
                              </div>
                              <p className="mt-2 text-sm text-sky-700">
                                Status atual do WhatsApp: {row.status_whatsapp || "pendente"}
                              </p>
                            </div>
                          </div>
                        </div>
                      </motion.article>
                    );
                  })}
              </AnimatePresence>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-3">
                <div className="text-sm text-gray-600">
                  Pagina {page} de {totalPages}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                  >
                    Anterior
                  </Button>
                  {pagesArray.map((pageNumber) => (
                    <Button
                      key={pageNumber}
                      variant={pageNumber === page ? "primary" : "ghost"}
                      size="sm"
                      onClick={() => setPage(pageNumber)}
                    >
                      {pageNumber}
                    </Button>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  >
                    Proximo
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.section>
      </div>
    </div>
  );

  const renderMessages = () => (
    <div className="space-y-4">
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0, transition: { type: "spring", stiffness: 100, damping: 18 } }}
        className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_380px]"
      >
        <Card className="relative overflow-hidden border-0 bg-graphite text-sand-50 shadow-[0_24px_60px_-32px_rgba(35,31,26,0.55)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(180,22,50,0.34),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.08),transparent_38%)]" />
          <CardHeader className="relative flex flex-col gap-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-sand-300/70">Mensageria</p>
                <h2 className="text-3xl font-semibold tracking-tight">Aba de envio</h2>
                <p className="mt-2 max-w-2xl text-sm text-sand-300/80">
                  Curadoria humana e automacao convivem na mesma superficie. Aqui voce seleciona,
                  aprova, coloca na fila e define o comportamento das proximas varreduras.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
                <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Proximo envio</p>
                <p className="text-lg font-semibold">
                  {schedulerStatus?.next_run_at ? formatDateTime(schedulerStatus.next_run_at) : "--"}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Modo apos busca</span>
              <button
                type="button"
                onClick={() => handleMessageModeChange("manual").catch(() => null)}
                disabled={busyModeChange}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition",
                  messageConfig?.modo_envio === "manual"
                    ? "border-white/20 bg-white text-graphite"
                    : "border-white/15 bg-white/6 text-sand-50 hover:bg-white/10"
                )}
              >
                Curadoria manual
              </button>
              <button
                type="button"
                onClick={() => handleMessageModeChange("automatico").catch(() => null)}
                disabled={busyModeChange}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition",
                  messageConfig?.modo_envio === "automatico"
                    ? "border-blush-200 bg-blush-50 text-accent"
                    : "border-white/15 bg-white/6 text-sand-50 hover:bg-white/10"
                )}
              >
                Automacao apos busca
              </button>
              <span className="text-xs text-sand-300/70">
                {messageConfig?.modo_envio === "automatico"
                  ? "Novos resultados elegiveis entram em aprovacao e fila automaticamente."
                  : "Novos resultados ficam na base ate voce selecionar e enfileirar manualmente."}
              </span>
            </div>
          </CardHeader>
          <CardContent className="relative grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Status</p>
                <p className="mt-2 text-2xl font-semibold">
                  {schedulerStatus?.running ? "Ativo" : "Pausado"}
                </p>
                <p className="mt-1 text-xs text-sand-300/75">
                  {schedulerStatus?.window_label || "Janela operacional nao carregada"}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Enviados hoje</p>
                <p className="mt-2 text-2xl font-semibold">{schedulerStatus?.sent_today ?? 0}</p>
                <p className="mt-1 text-xs text-sand-300/75">
                  Limite diario: {schedulerStatus?.daily_limit ?? 0}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Pendentes na fila</p>
                <p className="mt-2 text-2xl font-semibold">{schedulerStatus?.pending_items ?? queue.length}</p>
                <p className="mt-1 text-xs text-sand-300/75">
                  {resumo?.aguardando_envio ?? 0} aprovados aguardando envio
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <Button
                size="lg"
                onClick={() => handleDispatchAction("/api/disparo/iniciar").catch(() => null)}
                disabled={busyDispatch}
                className="w-full gap-2 rounded-2xl"
              >
                <PaperPlaneTilt size={18} />
                Iniciar disparo
              </Button>
              <Button
                variant="ghost"
                size="lg"
                onClick={() => handleDispatchAction("/api/disparo/pausar").catch(() => null)}
                disabled={busyDispatch}
                className="w-full rounded-2xl border border-white/10 bg-white/6 text-sand-50 hover:bg-white/10"
              >
                <PauseCircle size={18} />
                Pausar disparo
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden border-sand-200/90 bg-shell/92">
          <CardHeader className="border-b border-sand-200/80">
            <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Regras operacionais</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Janela e ritmo</h2>
          </CardHeader>
          <CardContent className="grid gap-3 pt-5">
            <MetaBlock
              label="Intervalo entre envios"
              value="30 minutos entre mensagens enviadas"
              tone="blush"
            />
            <MetaBlock
              label="Horario util"
              value={schedulerStatus?.window_label || "09:00-18:00 dias uteis"}
              tone="sky"
            />
            <MetaBlock
              label="Limite diario"
              value={`${schedulerStatus?.daily_limit ?? 0} mensagens por dia`}
              tone="sun"
            />
            <MetaBlock
              label="Ultimo erro"
              value={schedulerStatus?.last_error || "Sem falhas recentes"}
              tone="sage"
            />
          </CardContent>
        </Card>
      </motion.section>

      <Card className="overflow-hidden border-sand-200/90 bg-shell/90">
        <CardHeader className="border-b border-sand-200/80 bg-[linear-gradient(180deg,rgba(245,228,230,0.55),rgba(252,248,243,0.3))]">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px] xl:items-end">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Selecionar estabelecimentos</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Curadoria para disparo</h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-600">
                Escolha quem entra na fila sem sair da aba `Mensagens`. O modo automatico afeta
                as proximas varreduras; a selecao manual continua disponivel o tempo todo.
              </p>
            </div>
            <div className="rounded-2xl border border-sand-200 bg-white/70 px-4 py-3 text-sm text-gray-600">
              {filteredDispatchLeads.length} lead(s) visiveis para operacao
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-5">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
            <Input
              value={dispatchSearch}
              onChange={(event) => setDispatchSearch(event.target.value)}
              placeholder="Buscar por nome, cidade, categoria ou telefone"
              className="h-11 bg-white"
            />
            <select
              className={selectClassName}
              value={dispatchStateFilter}
              onChange={(event) => setDispatchStateFilter(event.target.value)}
            >
              <option value="all">Todos os estados</option>
              <option value="disponivel">Disponiveis</option>
              <option value="aprovado">Aprovados</option>
              <option value="na_fila">Na fila</option>
              <option value="erro">Erro</option>
              <option value="sem_whatsapp">Sem WhatsApp</option>
              <option value="enviado">Enviados</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sand-200/80 bg-white/70 px-4 py-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-sand-200 bg-sand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-gray-600">
                {selectedDispatchIds.length} selecionados
              </span>
              <Button variant="ghost" size="sm" onClick={toggleVisibleDispatchSelection}>
                {allDispatchVisibleSelected ? "Limpar visiveis" : "Selecionar visiveis"}
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={() => handleApproval(true, selectedDispatchIds).catch(() => null)}
                disabled={!selectedDispatchIds.length || busyApproval}
                className="gap-2"
              >
                <Checks size={16} />
                Aprovar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleApproval(false, selectedDispatchIds).catch(() => null)}
                disabled={!selectedDispatchIds.length || busyApproval}
                className="gap-2"
              >
                <PauseCircle size={16} />
                Remover aprovacao
              </Button>
              <Button
                size="sm"
                onClick={() => handleQueueSelection().catch(() => null)}
                disabled={!selectedDispatchIds.length || busyQueueSelection}
                className="gap-2"
              >
                <PaperPlaneTilt size={16} />
                Adicionar a fila
              </Button>
            </div>
          </div>

          {loadingDispatchLeads && (
            <div className="grid gap-3 xl:grid-cols-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="rounded-[1.45rem] border border-sand-200/90 bg-white/80 p-5">
                  <Skeleton className="h-7 w-2/5" />
                  <Skeleton className="mt-3 h-24" />
                </div>
              ))}
            </div>
          )}

          {!loadingDispatchLeads && filteredDispatchLeads.length === 0 && (
            <div className="rounded-[1.55rem] border border-sand-200/90 bg-white/80 px-6 py-14 text-center">
              <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Sem candidatos</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-graphite">
                Nenhum estabelecimento encontrado para esta selecao
              </h3>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
                {messagesError || "Ajuste a busca, troque o filtro de estado ou rode uma nova varredura."}
              </p>
            </div>
          )}

          {!loadingDispatchLeads && filteredDispatchLeads.length > 0 && (
            <div className="grid gap-3 xl:grid-cols-2">
              {filteredDispatchLeads.map((row, index) => {
                const rowId = typeof row.id === "number" ? row.id : undefined;
                const isSelected = Boolean(rowId && selectedDispatchIds.includes(rowId));
                const canSelect = !["na_fila", "erro", "sem_whatsapp", "enviado"].includes(
                  row.dispatch_state || ""
                );
                return (
                  <motion.article
                    key={`${row.id || row.nome || "dispatch"}-${index}`}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 92, damping: 18, delay: index * 0.02 }}
                    className={cn(
                      "rounded-[1.45rem] border bg-white/80 p-5 shadow-diffuse",
                      isSelected ? "border-accent/50 ring-2 ring-accent/10" : "border-sand-200/90"
                    )}
                  >
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <label
                              className={cn(
                                "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                                canSelect
                                  ? "border-sand-200 bg-sand-50 text-gray-600"
                                  : "border-sand-200/80 bg-sand-100 text-gray-400"
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleDispatchSelection(rowId)}
                                disabled={!canSelect}
                                className="h-4 w-4 rounded border-sand-300 text-accent focus:ring-accent/30"
                              />
                              Selecionar
                            </label>
                            <span
                              className={cn(
                                "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                                dispatchStateTone(row.dispatch_state)
                              )}
                            >
                              {formatDispatchState(row.dispatch_state)}
                            </span>
                            {row.queue_origem_disparo && (
                              <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                                Origem {formatDispatchOrigin(row.queue_origem_disparo)}
                              </span>
                            )}
                          </div>
                          <h3 className="mt-3 break-words text-2xl font-semibold tracking-tight text-graphite">
                            {row.nome || "Lead sem nome"}
                          </h3>
                          <p className="mt-1 text-sm text-gray-600">
                            {formatLocation(row.cidade, row.bairro)}
                            {row.categoria ? ` - ${row.categoria}` : ""}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-sand-200 bg-sand-50 px-4 py-3 text-right">
                          <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Telefone</p>
                          <p className="mt-1 font-mono text-sm text-graphite">{row.telefone || "--"}</p>
                        </div>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <MetaBlock label="Fonte" value={formatSource(row.fonte)} tone="sky" />
                        <MetaBlock label="Status WhatsApp" value={row.status_whatsapp || "pendente"} tone="sage" />
                        <MetaBlock
                          label="Aprovacao"
                          value={row.aprovado_disparo ? "Aprovado" : "Nao aprovado"}
                          tone="sun"
                        />
                        <MetaBlock
                          label="Fila"
                          value={
                            row.queue_item_id
                              ? `${formatDispatchOrigin(row.queue_origem_disparo)} em ${formatDateTime(
                                  row.queue_data_agendamento
                                )}`
                              : "Ainda fora da fila"
                          }
                          tone="blush"
                        />
                      </div>
                    </div>
                  </motion.article>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-sand-200/90 bg-shell/88">
        <CardHeader className="border-b border-sand-200/80 bg-[linear-gradient(180deg,rgba(34,29,25,0.03),rgba(252,248,243,0.3))]">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Fila de disparos</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Sequencia operacional</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                Cada item registra origem, status, tentativas, agendamento, envio e erro.
              </p>
            </div>
            <div className="rounded-2xl border border-sand-200 bg-white/70 px-4 py-3 text-sm text-gray-600">
              Atualizacao automatica a cada 10s enquanto a aba estiver aberta
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-5">
          {loadingQueue && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="rounded-[1.4rem] border border-sand-200/85 bg-white/80 p-5"
                >
                  <Skeleton className="h-6 w-2/5" />
                  <Skeleton className="mt-3 h-20" />
                </div>
              ))}
            </div>
          )}

          {!loadingQueue && queue.length === 0 && (
            <div className="rounded-[1.55rem] border border-sand-200/90 bg-white/80 px-6 py-14 text-center">
              <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Fila vazia</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-graphite">
                Nenhum disparo preparado ainda
              </h3>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
                {messagesError || "Use a curadoria desta aba para aprovar e adicionar estabelecimentos a fila."}
              </p>
            </div>
          )}

          {!loadingQueue &&
            queue.map((item) => (
              <div
                key={item.id}
                className="rounded-[1.4rem] border border-sand-200/85 bg-white/80 p-5 shadow-diffuse"
              >
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_320px]">
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={cn("inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]", statusTone(item.status))}>
                            {item.status || "pendente"}
                          </span>
                          <span className="rounded-full border border-sand-200 bg-sand-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-600">
                            Tentativas {item.tentativas ?? 0}
                          </span>
                          <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                            Origem {formatDispatchOrigin(item.origem_disparo)}
                          </span>
                        </div>
                        <h3 className="mt-3 text-2xl font-semibold tracking-tight text-graphite">
                          {item.nome || "Lead sem nome"}
                        </h3>
                        <p className="mt-1 text-sm text-gray-600">
                          {formatLocation(item.cidade, undefined)}{item.categoria ? ` - ${item.categoria}` : ""}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-sand-200 bg-sand-50 px-4 py-3 text-right">
                        <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Telefone</p>
                        <p className="mt-1 font-mono text-sm text-graphite">{item.telefone || "--"}</p>
                      </div>
                    </div>

                    <details className="rounded-2xl border border-sand-200 bg-shell/85">
                      <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-graphite">
                        Visualizar mensagem gerada
                      </summary>
                      <div className="border-t border-sand-200 px-4 py-4 text-sm leading-relaxed text-gray-700">
                        <pre className="whitespace-pre-wrap font-sans">{item.mensagem || "Sem mensagem registrada."}</pre>
                      </div>
                    </details>

                    {item.erro_descricao && (
                      <div className="rounded-2xl border border-blush-200 bg-blush-50/80 px-4 py-3 text-sm text-blush-700">
                        <div className="flex items-start gap-2">
                          <WarningCircle size={18} className="mt-0.5 shrink-0" />
                          <div>
                            <p className="font-semibold">Erro registrado</p>
                            <p className="mt-1">{item.erro_descricao}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                    <MetaBlock
                      label="Agendado para"
                      value={formatDateTime(item.data_agendamento)}
                      tone="sky"
                    />
                    <MetaBlock
                      label="Enviado em"
                      value={formatDateTime(item.data_envio)}
                      tone="sage"
                    />
                    <MetaBlock
                      label="Status operacional"
                      value={item.status || "pendente"}
                      tone="sun"
                    />
                    <MetaBlock
                      label="Leitura rapida"
                      value={
                        item.status === "erro"
                          ? "Exige revisao"
                          : item.status === "sem_whatsapp"
                            ? "Numero descartado"
                            : item.status === "enviado"
                              ? "Aguardando retorno"
                              : "Na fila de execucao"
                      }
                      tone="blush"
                    />
                  </div>
                </div>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="min-h-[100dvh] overflow-x-hidden bg-canvas text-graphite">
      <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <motion.header
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0, transition: { type: "spring", stiffness: 120, damping: 18 } }}
            className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]"
          >
            <div className="space-y-3">
              <span className="inline-flex w-fit items-center rounded-full border border-blush-200 bg-blush-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-blush-700">
                Sala de operacoes comercial
              </span>
              <div>
                <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
                  Bot de Inteligencia Comercial
                </h1>
                <p className="mt-3 max-w-3xl text-base leading-relaxed text-gray-600">
                  O shell principal agora separa descoberta de leads e execucao de mensagens.
                  A primeira aba organiza a base. A segunda opera fila, janela de envio,
                  pausas e erros sem misturar tudo no mesmo fluxo.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-start justify-start gap-3 lg:justify-end">
              <Button variant="ghost" size="sm" onClick={() => refreshAll().catch(() => null)} className="gap-2">
                <ArrowClockwise size={18} />
                Atualizar
              </Button>
              <Button variant="ghost" size="sm" onClick={() => window.open(`/api/export/csv?${exportQuery}`, "_blank")} className="gap-2">
                <DownloadSimple size={18} />
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => window.open(`/api/export/xlsx?${exportQuery}`, "_blank")} className="gap-2">
                <DownloadSimple size={18} />
                XLSX
              </Button>
            </div>
          </motion.header>

          <Card className="overflow-hidden border-sand-200/90 bg-shell/90">
            <CardHeader className="border-b border-sand-200/80 pb-5">
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => setActiveTab("estabelecimentos")}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition",
                    activeTab === "estabelecimentos"
                      ? "border-accent bg-accent text-white"
                      : "border-sand-200 bg-white/80 text-graphite hover:bg-white"
                  )}
                >
                  <Checks size={16} />
                  Estabelecimentos
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("mensagens")}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition",
                    activeTab === "mensagens"
                      ? "border-graphite bg-graphite text-sand-50"
                      : "border-sand-200 bg-white/80 text-graphite hover:bg-white"
                  )}
                >
                  <PaperPlaneTilt size={16} />
                  Mensagens
                </button>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 pt-5 md:grid-cols-2 xl:grid-cols-4">
              {loadingKpi ? (
                <>
                  <Skeleton className="h-36" />
                  <Skeleton className="h-36" />
                  <Skeleton className="h-36" />
                  <Skeleton className="h-36" />
                </>
              ) : (
                resumo && (
                  <>
                    <motion.div variants={stagger} initial="hidden" animate="show" custom={0}>
                      <KpiCard
                        label="Base ativa"
                        value={resumo.total}
                        helper={`${resumo.alta} leads de alta prioridade e score medio ${resumo.score_medio?.toFixed(1) ?? "0.0"}.`}
                        tone="sky"
                      />
                    </motion.div>
                    <motion.div variants={stagger} initial="hidden" animate="show" custom={1}>
                      <KpiCard
                        label="Aprovados"
                        value={resumo.aprovados}
                        helper={`${resumo.aguardando_envio} aguardando envio com status pendente.`}
                        tone="sage"
                      />
                    </motion.div>
                    <motion.div variants={stagger} initial="hidden" animate="show" custom={2}>
                      <KpiCard
                        label="Enviados hoje"
                        value={resumo.enviados_hoje}
                        helper={schedulerStatus ? `Scheduler ${schedulerStatus.running ? "ativo" : "pausado"}.` : "Pronto para operacao."}
                        tone="blush"
                      />
                    </motion.div>
                    <motion.div variants={stagger} initial="hidden" animate="show" custom={3}>
                      <KpiCard
                        label="Ultima coleta"
                        value={formatDateTime(resumo.ultima_coleta)}
                        helper="Leitura consolidada da base local."
                        tone="sun"
                      />
                    </motion.div>
                  </>
                )
              )}
            </CardContent>
          </Card>

          {activeTab === "estabelecimentos" ? renderEstablishments() : renderMessages()}
        </div>
      </div>
    </div>
  );
}
