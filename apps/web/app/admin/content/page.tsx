"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  adminListContent,
  adminPublishContent,
  adminUnpublishContent,
  adminDeleteContent,
  type AdminContent,
} from "@/lib/admin-api";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-[rgba(255,255,255,0.08)] text-ash",
  pending_review: "bg-[rgba(255,138,89,0.15)] text-[#FF8A59]",
  published: "bg-[rgba(89,255,180,0.15)] text-[#59FFB4]",
  retracted: "bg-[rgba(255,89,89,0.15)] text-[#FF5959]",
};

export default function AdminContentPage() {
  const [items, setItems] = useState<AdminContent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  async function loadContent() {
    setLoading(true);
    try {
      const data = await adminListContent({
        search: search || undefined,
        status: statusFilter || undefined,
        content_type: typeFilter || undefined,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to load content:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadContent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, typeFilter]);

  async function handlePublish(slug: string) {
    try {
      await adminPublishContent(slug);
      await loadContent();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao publicar");
    }
  }

  async function handleUnpublish(slug: string) {
    try {
      await adminUnpublishContent(slug);
      await loadContent();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao despublicar");
    }
  }

  async function handleDelete(slug: string) {
    if (!confirm(`Deletar "${slug}"?`)) return;
    try {
      await adminDeleteContent(slug);
      await loadContent();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao deletar");
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-[28px] text-sinal-white">Conteudos</h1>
          <p className="mt-1 font-mono text-[12px] text-ash">{total} itens</p>
        </div>
        <Link
          href="/admin/content/new"
          className="rounded-lg bg-signal px-4 py-2 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim"
        >
          + Novo conteudo
        </Link>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por titulo..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && loadContent()}
          className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-sinal-graphite px-3 py-2 font-mono text-[13px] text-bone placeholder-ash outline-none focus:border-signal"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-sinal-graphite px-3 py-2 font-mono text-[13px] text-bone outline-none"
        >
          <option value="">Todos os status</option>
          <option value="draft">Draft</option>
          <option value="pending_review">Pending Review</option>
          <option value="published">Published</option>
          <option value="retracted">Retracted</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-[rgba(255,255,255,0.1)] bg-sinal-graphite px-3 py-2 font-mono text-[13px] text-bone outline-none"
        >
          <option value="">Todos os tipos</option>
          <option value="ARTICLE">Article</option>
          <option value="POST">Post</option>
          <option value="HOWTO">How-to</option>
          <option value="DATA_REPORT">Data Report</option>
          <option value="ANALYSIS">Analysis</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <p className="py-8 text-center font-mono text-[13px] text-ash">Carregando...</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center font-mono text-[13px] text-ash">
          Nenhum conteudo encontrado.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[rgba(255,255,255,0.06)]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
                <th className="px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[1px] text-ash">
                  Titulo
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[1px] text-ash">
                  Tipo
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[1px] text-ash">
                  Status
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[1px] text-ash">
                  Data
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-semibold uppercase tracking-[1px] text-ash">
                  Acoes
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-[rgba(255,255,255,0.04)] transition-colors hover:bg-[rgba(255,255,255,0.02)]"
                >
                  <td className="max-w-[400px] truncate px-4 py-3 text-[14px] text-bone">
                    {item.title}
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px] text-ash">{item.content_type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-md px-2 py-0.5 font-mono text-[11px] ${STATUS_COLORS[item.review_status] ?? STATUS_COLORS.draft}`}
                    >
                      {item.review_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px] text-ash">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString("pt-BR") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/content/${item.slug}/edit`}
                        className="font-mono text-[12px] text-signal hover:underline"
                      >
                        Editar
                      </Link>
                      <Link
                        href={`/admin/content/${item.slug}/preview`}
                        className="font-mono text-[12px] text-ash hover:text-bone hover:underline"
                      >
                        Preview
                      </Link>
                      {item.review_status === "published" ? (
                        <button
                          onClick={() => handleUnpublish(item.slug)}
                          className="font-mono text-[12px] text-ash hover:text-[#FF8A59]"
                        >
                          Despublicar
                        </button>
                      ) : (
                        <button
                          onClick={() => handlePublish(item.slug)}
                          className="font-mono text-[12px] text-[#59FFB4] hover:underline"
                        >
                          Publicar
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(item.slug)}
                        className="font-mono text-[12px] text-ash hover:text-[#FF5959]"
                      >
                        Deletar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
