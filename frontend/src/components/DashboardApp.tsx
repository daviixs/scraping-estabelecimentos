/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Badge } from "./ui/badge";
import { Skeleton } from "./ui/skeleton";
import { Input } from "./ui/input";
import { ArrowUpRight, DownloadSimple, FunnelSimple, ArrowClockwise } from "@phosphor-icons/react";
import ScanCommander from "./ScanCommander";
import { cn } from "../lib/utils";

type Estabelecimento = {
  id?: number;
  nome?: string;
  categoria?: string;
  cidade?: string;
  bairro?: string;
  nota_media?: number;
  total_avaliacoes?: number;
  score_oportunidade?: number;
  prioridade_lead?: string;
  resumo_queixas?: string;
  fonte?: string;
  data_coleta?: string;
  link_origem?: string;
};

type Resumo = {
  total: number;
  alta: number;
  media: number;
  baixa: number;
  score_medio: number;
  ultima_coleta: string;
};

const stagger = {
  hidden: { opacity: 0, y: 12 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.04, type: "spring", stiffness: 90, damping: 16 },
  }),
};

const badgeColor: Record<string, string> = {
  ALTA: "bg-red-100 text-red-800 border border-red-200",
  "MÉDIA": "bg-amber-100 text-amber-800 border border-amber-200",
  BAIXA: "bg-emerald-100 text-emerald-800 border border-emerald-200",
};

const scoreBarColor = (score?: number) => {
  if (score === undefined || score === null) return "bg-sand-300";
  if (score >= 60) return "bg-accent";
  if (score >= 35) return "bg-amber-400";
  return "bg-red-500";
};

export default function DashboardApp() {
  const [data, setData] = useState<Estabelecimento[]>([]);
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
  const [error, setError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState({
    classificacao: [] as string[],
    prioridade: [] as string[],
    fonte: [] as string[],
    cidade: "",
    categoria: "",
    score_min: 0,
  });

  const queryString = (params: Record<string, any>) =>
    Object.entries(params)
      .filter(([_, v]) => v !== null && v !== undefined && v !== "" && (!(Array.isArray(v)) || v.length > 0))
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(Array.isArray(v) ? v.join(",") : v)}`)
      .join("&");

  const fetchResumo = async () => {
    setLoadingKpi(true);
    try {
      const res = await fetch("/api/resumo");
      const json = await res.json();
      setResumo(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingKpi(false);
    }
  };

  const fetchFiltros = async () => {
    try {
      const [c, cat] = await Promise.all([fetch("/api/cidades").then((r) => r.json()), fetch("/api/categorias").then((r) => r.json())]);
      setCidades(c);
      setCategorias(cat);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchData = async () => {
    setLoadingTable(true);
    setError(null);
    const query = queryString({
      ...filtros,
      page,
      per_page: perPage,
      order_by: orderBy,
      order_dir: orderDir,
    });
    try {
      const res = await fetch(`/api/estabelecimentos?${query}`);
      if (!res.ok) throw new Error("Erro ao carregar dados");
      const json = await res.json();
      setData(json.data);
      setPages(json.pages);
      setTotal(json.total);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar");
      setData([]);
    } finally {
      setLoadingTable(false);
    }
  };

  useEffect(() => {
    fetchResumo();
    fetchFiltros();
  }, []);

  useEffect(() => {
    fetchData();
  }, [page, orderBy, orderDir, filtros, perPage]);

  const toggleArray = (field: "classificacao" | "prioridade" | "fonte", value: string) => {
    setFiltros((prev) => {
      const exists = prev[field].includes(value);
      return { ...prev, [field]: exists ? prev[field].filter((v) => v !== value) : [...prev[field], value] };
    });
    setPage(1);
  };

  const limpar = () => {
    setFiltros({ classificacao: [], prioridade: [], fonte: [], cidade: "", categoria: "", score_min: 0 });
    setPage(1);
  };

  const orderToggle = (col: string) => {
    if (orderBy === col) {
      setOrderDir(orderDir === "asc" ? "desc" : "asc");
    } else {
      setOrderBy(col);
      setOrderDir("asc");
    }
  };

  const exportar = (fmt: "csv" | "xlsx") => {
    const query = queryString({ ...filtros });
    window.open(`/api/export/${fmt}?${query}`, "_blank");
  };

  const refreshAll = () => {
    fetchResumo();
    fetchFiltros();
    fetchData();
  };

  const prioridadeBadge = (prior?: string) => <Badge label={prior} className={badgeColor[prior || ""]} />;

  const pagesArray = useMemo(() => {
    const arr = [];
    const start = Math.max(1, page - 2);
    const end = Math.min(pages, start + 4);
    for (let i = start; i <= end; i++) arr.push(i);
    return arr;
  }, [page, pages]);

  return (
    <div className="min-h-[100dvh] bg-sand-100 text-graphite">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0, transition: { type: "spring", stiffness: 120, damping: 18 } }}
          className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
        >
          <div>
            <p className="text-sm tracking-tight text-gray-500">Dashboard de Leads</p>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">Bot de Inteligência Comercial</h1>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <Button variant="ghost" size="sm" onClick={() => fetchData()} className="flex items-center gap-2">
              <ArrowClockwise size={18} /> Atualizar
            </Button>
            <Button variant="ghost" size="sm" onClick={() => exportar("csv")} className="flex items-center gap-2">
              <DownloadSimple size={18} /> CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => exportar("xlsx")} className="flex items-center gap-2">
              <DownloadSimple size={18} /> XLSX
            </Button>
          </div>
        </motion.header>

        <ScanCommander onFinished={refreshAll} />

        <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {loadingKpi ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-3xl" />)
          ) : (
            resumo && (
              <>
                {[
                  { label: "Total", value: resumo.total, sub: "estabelecimentos" },
                  { label: "Prioridade Alta", value: resumo.alta, sub: "leads quentes" },
                  { label: "Score médio", value: resumo.score_medio?.toFixed(1) ?? "0.0", sub: "última coleta" },
                  { label: "Última coleta", value: resumo.ultima_coleta || "—", sub: "" },
                ].map((item, i) => (
                  <motion.div key={item.label} variants={stagger} initial="hidden" animate="show" custom={i}>
                    <Card className="bg-white/90 border-sand-200">
                      <CardHeader className="pb-2">
                        <p className="text-sm text-gray-500">{item.label}</p>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="flex items-baseline gap-2">
                          <motion.span
                            layout
                            className="text-3xl font-semibold tracking-tight"
                            initial={{ opacity: 0.5 }}
                            animate={{ opacity: 1 }}
                            transition={{ type: "spring", stiffness: 100, damping: 20 }}
                          >
                            {item.value}
                          </motion.span>
                          {item.sub && <span className="text-sm text-gray-500">{item.sub}</span>}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </>
            )
          )}
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <motion.aside
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0, transition: { type: "spring", stiffness: 110, damping: 18 } }}
            className="lg:col-span-4 space-y-4"
          >
            <Card className="bg-white/90">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <p className="text-sm text-gray-500">Filtros</p>
                  <h3 className="text-lg font-semibold">Refine os leads</h3>
                </div>
                <div className="h-10 w-10 rounded-full bg-accent/10 text-accent flex items-center justify-center">
                  <FunnelSimple size={18} />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-sm font-semibold">Classificação</p>
                  {["MUITO BOM", "MÉDIO", "MUITO RUIM"].map((c) => (
                    <div key={c} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filtros.classificacao.includes(c)}
                        onChange={() => toggleArray("classificacao", c)}
                        className="h-4 w-4 rounded border-sand-300 text-accent focus:ring-2 focus:ring-accent/50"
                      />
                      <span className="text-sm">{c}</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-semibold">Prioridade</p>
                  {["ALTA", "MÉDIA", "BAIXA"].map((c) => (
                    <div key={c} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filtros.prioridade.includes(c)}
                        onChange={() => toggleArray("prioridade", c)}
                        className="h-4 w-4 rounded border-sand-300 text-accent focus:ring-2 focus:ring-accent/50"
                      />
                      <span className="text-sm">{c}</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-semibold">Fonte</p>
                  {["google_maps", "apontador", "manual"].map((c) => (
                    <div key={c} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filtros.fonte.includes(c)}
                        onChange={() => toggleArray("fonte", c)}
                        className="h-4 w-4 rounded border-sand-300 text-accent focus:ring-2 focus:ring-accent/50"
                      />
                      <span className="text-sm capitalize">{c.replace("_", " ")}</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-semibold">Cidade</p>
                  <select
                    className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-accent/50"
                    value={filtros.cidade}
                    onChange={(e) => {
                      setFiltros((p) => ({ ...p, cidade: e.target.value }));
                      setPage(1);
                    }}
                  >
                    <option value="">Todas</option>
                    {cidades.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-semibold">Categoria</p>
                  <select
                    className="w-full rounded-xl border border-sand-200 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-accent/50"
                    value={filtros.categoria}
                    onChange={(e) => {
                      setFiltros((p) => ({ ...p, categoria: e.target.value }));
                      setPage(1);
                    }}
                  >
                    <option value="">Todas</option>
                    {categorias.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm font-semibold">
                    <span>Score mínimo</span>
                    <span className="text-accent">{filtros.score_min}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={filtros.score_min}
                    onChange={(e) => {
                      setFiltros((p) => ({ ...p, score_min: Number(e.target.value) }));
                      setPage(1);
                    }}
                    className="w-full accent-accent"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <Button variant="primary" className="flex-1" onClick={() => fetchData()}>
                    Aplicar
                  </Button>
                  <Button variant="ghost" className="flex-1" onClick={limpar}>
                    Limpar
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.aside>

          <motion.section
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0, transition: { type: "spring", stiffness: 110, damping: 18 } }}
            className="lg:col-span-8 space-y-3"
          >
            <Card className="bg-white/95">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                  <p className="text-sm text-gray-500">Resultados</p>
                  <h3 className="text-lg font-semibold">Estabelecimentos</h3>
                </div>
                <div className="text-sm text-gray-500">
                  Mostrando {total === 0 ? 0 : (page - 1) * perPage + 1}–{Math.min(page * perPage, total)} de {total}
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="overflow-x-auto relative scroll-shadow">
                  <table className="min-w-full text-sm">
                    <thead className="sticky top-0 bg-white">
                      <tr className="text-xs uppercase text-gray-500">
                        {[
                          ["nome", "Nome"],
                          ["categoria", "Categoria"],
                          ["cidade", "Cidade/Bairro"],
                          ["nota_media", "Nota"],
                          ["total_avaliacoes", "Avaliações"],
                          ["score_oportunidade", "Score"],
                          ["prioridade_lead", "Prioridade"],
                          ["resumo_queixas", "Queixas"],
                          ["fonte", "Fonte"],
                          ["data_coleta", "Coleta"],
                        ].map(([key, label]) => (
                          <th
                            key={key}
                            className="px-3 py-2 text-left cursor-pointer select-none"
                            onClick={() => orderToggle(key)}
                          >
                            <span className="inline-flex items-center gap-1">
                              {label}
                              {orderBy === key && <ArrowUpRight size={12} className={cn(orderDir === "asc" ? "rotate-180" : "")} />}
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {loadingTable &&
                        Array.from({ length: 6 }).map((_, i) => (
                          <tr key={i} className="border-b border-sand-200/70">
                            <td className="px-3 py-3" colSpan={10}>
                              <Skeleton className="h-6" />
                            </td>
                          </tr>
                        ))}

                      {!loadingTable && data.length === 0 && (
                        <tr>
                          <td colSpan={10} className="py-10 text-center text-gray-500">
                            {error || "Nenhum resultado encontrado."}
                          </td>
                        </tr>
                      )}

                      <AnimatePresence>
                        {!loadingTable &&
                          data.map((row, i) => (
                            <motion.tr
                              key={`${row.nome}-${row.cidade}-${i}`}
                              initial={{ opacity: 0, y: 6 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0 }}
                              transition={{ type: "spring", stiffness: 90, damping: 16, delay: i * 0.02 }}
                              className="border-b border-sand-200/60 hover:bg-sand-50/70"
                            >
                              <td className="px-3 py-3">
                                <a
                                  href={row.link_origem || "#"}
                                  target="_blank"
                                  className="font-semibold hover:text-accent transition"
                                >
                                  {row.nome}
                                </a>
                              </td>
                              <td className="px-3 py-3 text-gray-700">{row.categoria || "—"}</td>
                              <td className="px-3 py-3 text-gray-700">
                                {row.cidade || "—"}
                                {row.bairro ? ` / ${row.bairro}` : ""}
                              </td>
                              <td className="px-3 py-3 font-semibold">
                                <span
                                  className={cn(
                                    row.nota_media !== undefined && row.nota_media >= 4.8
                                      ? "text-emerald-600"
                                      : row.nota_media !== undefined && row.nota_media >= 4.5
                                      ? "text-amber-600"
                                      : "text-red-600"
                                  )}
                                >
                                  {row.nota_media !== undefined && row.nota_media !== null ? row.nota_media.toFixed(1) : "—"}
                                </span>
                              </td>
                              <td className="px-3 py-3 font-mono text-sm text-gray-700">{row.total_avaliacoes ?? "—"}</td>
                              <td className="px-3 py-3">
                                <div className="flex items-center gap-2">
                                  <div className="h-2 w-28 rounded-full bg-sand-200 overflow-hidden">
                                    <motion.div
                                      className={cn("h-full", scoreBarColor(row.score_oportunidade))}
                                      initial={{ width: 0 }}
                                      animate={{ width: `${Math.min(Math.max(row.score_oportunidade || 0, 0), 100)}%` }}
                                      transition={{ type: "spring", stiffness: 90, damping: 15 }}
                                    />
                                  </div>
                                  <span className="font-mono text-xs text-gray-600">
                                    {(row.score_oportunidade ?? 0).toFixed(1)}
                                  </span>
                                </div>
                              </td>
                              <td className="px-3 py-3">{prioridadeBadge(row.prioridade_lead)}</td>
                              <td className="px-3 py-3 text-gray-700">{row.resumo_queixas || "—"}</td>
                              <td className="px-3 py-3 text-gray-700 capitalize">{row.fonte || "—"}</td>
                              <td className="px-3 py-3 text-gray-700">{row.data_coleta || "—"}</td>
                            </motion.tr>
                          ))}
                      </AnimatePresence>
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center justify-between pt-4 flex-wrap gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">Por página</span>
                    <Input
                      type="number"
                      className="w-20"
                      min={5}
                      max={100}
                      value={perPage}
                      onChange={(e) => {
                        setPerPage(Number(e.target.value));
                        setPage(1);
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                      « Anterior
                    </Button>
                    {pagesArray.map((p) => (
                      <Button
                        key={p}
                        variant={p === page ? "primary" : "ghost"}
                        size="sm"
                        onClick={() => setPage(p)}
                        className={cn(p === page ? "" : "border border-sand-200")}
                      >
                        {p}
                      </Button>
                    ))}
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={page >= pages}
                      onClick={() => setPage((p) => Math.min(pages, p + 1))}
                    >
                      Próximo »
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.section>
        </div>
      </div>
    </div>
  );
}
