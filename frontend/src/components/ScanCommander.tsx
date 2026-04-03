"use client";
import React, { useEffect, useRef, useState } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Input } from "./ui/input";
import { cn } from "../lib/utils";

type ScanJob = {
  id: string;
  command: string;
  fonte: string;
  status: "queued" | "running" | "completed" | "partial" | "error";
  meta_minima: number;
  novos_encontrados: number;
  ignorados_existentes: number;
  paginas_percorridas: number;
  registros_inspecionados: number;
  mensagem: string;
  erro?: string | null;
};

const examples = [
  "google_maps restaurantes Franca SP",
  "apontador Franca SP bares-e-restaurantes/restaurantes",
  'python main.py --fonte google_maps --busca "restaurantes Franca SP"',
];

const statusLabel: Record<ScanJob["status"], string> = {
  queued: "Na fila",
  running: "Em execucao",
  completed: "Concluida",
  partial: "Parcial",
  error: "Erro",
};

const statusTone: Record<ScanJob["status"], string> = {
  queued: "border-white/20 bg-white/8 text-sand-50",
  running: "border-accent/40 bg-accent/15 text-sand-50",
  completed: "border-emerald-300/50 bg-emerald-400/15 text-sand-50",
  partial: "border-amber-300/50 bg-amber-400/15 text-sand-50",
  error: "border-red-300/50 bg-red-500/15 text-sand-50",
};

export default function ScanCommander({ onFinished }: { onFinished: () => void }) {
  const [command, setCommand] = useState("");
  const [job, setJob] = useState<ScanJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const syncedTerminalState = useRef<string | null>(null);

  const fetchJob = async (jobId: string) => {
    try {
      const res = await fetch(`/api/varreduras/${jobId}`);
      if (!res.ok) return;
      const json = await res.json();
      setJob(json.job);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await fetch("/api/varreduras/ativa");
      if (!res.ok) return;
      const json = await res.json();
      if (json.job) {
        setJob(json.job);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchLatest();
  }, []);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const intervalId = window.setInterval(() => fetchJob(job.id), 2000);
    return () => window.clearInterval(intervalId);
  }, [job?.id, job?.status]);

  useEffect(() => {
    if (!job || ["queued", "running"].includes(job.status)) return;
    const syncKey = `${job.id}:${job.status}`;
    if (syncedTerminalState.current === syncKey) return;
    syncedTerminalState.current = syncKey;
    onFinished();
  }, [job, onFinished]);

  const startScan = async () => {
    const trimmed = command.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/varreduras", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: trimmed }),
      });
      const json = await res.json();
      if (!res.ok) {
        if (json.job) setJob(json.job);
        throw new Error(json.error || "Nao foi possivel iniciar a varredura.");
      }
      setJob(json.job);
    } catch (err: any) {
      setError(err.message || "Nao foi possivel iniciar a varredura.");
    } finally {
      setSubmitting(false);
    }
  };

  const running = !!job && ["queued", "running"].includes(job.status);

  return (
    <Card className="relative overflow-hidden border-0 bg-graphite text-sand-50 shadow-[0_24px_60px_-32px_rgba(35,31,26,0.55)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(180,22,50,0.34),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.1),transparent_38%)]" />
      <CardHeader className="relative flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-sand-300/70">Operacao</p>
          <h2 className="text-2xl font-semibold tracking-tight">Procurar estabelecimentos</h2>
          <p className="mt-2 max-w-2xl text-sm text-sand-300/80">
            Dispare uma varredura por comando livre. A busca continua ate atingir 30 novos estabelecimentos ou
            esgotar a fonte.
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
          <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Meta minima</p>
          <p className="text-2xl font-semibold">30 novos</p>
        </div>
      </CardHeader>
      <CardContent className="relative space-y-5">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
          <div className="space-y-3">
            <Input
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="google_maps restaurantes Franca SP"
              className="h-14 rounded-2xl border-white/10 bg-white/10 px-4 font-mono text-[15px] text-sand-50 placeholder:text-sand-300/45 focus:border-accent/60 focus:ring-accent/40"
              disabled={submitting || running}
            />
            <div className="flex flex-wrap gap-2">
              {examples.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setCommand(example)}
                  className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs font-medium text-sand-200 transition hover:border-white/20 hover:bg-white/10"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <Button size="lg" onClick={startScan} disabled={submitting || running || !command.trim()} className="w-full rounded-2xl">
              {submitting || running ? "Executando..." : "Executar varredura"}
            </Button>
            <Button
              variant="ghost"
              size="lg"
              onClick={() => fetchLatest()}
              className="w-full rounded-2xl border border-white/10 bg-white/6 text-sand-50 hover:bg-white/10"
            >
              Recuperar status
            </Button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div className={cn("rounded-2xl border px-4 py-4", job ? statusTone[job.status] : "border-white/10 bg-white/6")}>
            <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Status</p>
            <p className="mt-2 text-xl font-semibold">{job ? statusLabel[job.status] : "Ocioso"}</p>
            <p className="mt-1 text-xs text-sand-300/70">{job?.fonte ? job.fonte.replace("_", " ") : "Aguardando comando"}</p>
          </div>
          {[
            ["Novos", job?.novos_encontrados ?? 0],
            ["Ignorados", job?.ignorados_existentes ?? 0],
            ["Paginas", job?.paginas_percorridas ?? 0],
            ["Inspecionados", job?.registros_inspecionados ?? 0],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/6 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">{label}</p>
              <p className="mt-2 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.24em] text-sand-300/70">Mensagem da execucao</p>
          <p className="mt-2 text-sm text-sand-100">{error || job?.erro || job?.mensagem || "Nenhuma varredura executada nesta sessao."}</p>
          {job?.command && <p className="mt-3 break-all font-mono text-xs text-sand-300/75">{job.command}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
