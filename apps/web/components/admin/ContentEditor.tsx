"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";

const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

export interface ContentEditorData {
  title: string;
  subtitle: string;
  body_md: string;
  content_type: string;
  summary: string;
  meta_description: string;
  sources: string[];
  author_name: string;
}

// eslint-disable-next-line no-unused-vars
type EditorCallback = (d: ContentEditorData) => Promise<void>;

interface ContentEditorProps {
  initialData?: Partial<ContentEditorData>;
  onSave: EditorCallback;
  onPublish?: EditorCallback;
  saving?: boolean;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[àáâãäå]/g, "a")
    .replace(/[èéêë]/g, "e")
    .replace(/[ìíîï]/g, "i")
    .replace(/[òóôõö]/g, "o")
    .replace(/[ùúûü]/g, "u")
    .replace(/[ñ]/g, "n")
    .replace(/[ç]/g, "c")
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

const CONTENT_TYPES = [
  { value: "ARTICLE", label: "Artigo" },
  { value: "POST", label: "Post" },
  { value: "HOWTO", label: "How-to" },
];

export default function ContentEditor({
  initialData,
  onSave,
  onPublish,
  saving,
}: ContentEditorProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [subtitle, setSubtitle] = useState(initialData?.subtitle ?? "");
  const [authorName, setAuthorName] = useState(initialData?.author_name ?? "");
  const [bodyMd, setBodyMd] = useState(initialData?.body_md ?? "");
  const [contentType, setContentType] = useState(initialData?.content_type ?? "ARTICLE");
  const [summary, setSummary] = useState(initialData?.summary ?? "");
  const [metaDescription, setMetaDescription] = useState(initialData?.meta_description ?? "");
  const [sources, setSources] = useState<string[]>(initialData?.sources ?? []);
  const [newSource, setNewSource] = useState("");

  const slug = slugify(title);

  const getData = useCallback(
    (): ContentEditorData => ({
      title,
      subtitle,
      body_md: bodyMd,
      content_type: contentType,
      summary,
      meta_description: metaDescription,
      sources,
      author_name: authorName,
    }),
    [title, subtitle, bodyMd, contentType, summary, metaDescription, sources, authorName],
  );

  function addSource() {
    const url = newSource.trim();
    if (url && !sources.includes(url)) {
      setSources([...sources, url]);
      setNewSource("");
    }
  }

  function removeSource(index: number) {
    setSources(sources.filter((_, i) => i !== index));
  }

  const inputClass =
    "w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-sinal-graphite px-3 py-2 font-mono text-[13px] text-bone placeholder-ash outline-none focus:border-signal";

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Titulo *
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Titulo do conteudo"
          className={inputClass}
        />
        {slug && (
          <p className="mt-1 font-mono text-[11px] text-ash">
            Slug: <span className="text-signal">{slug}</span>
          </p>
        )}
      </div>

      {/* Subtitle */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Subtitulo
        </label>
        <input
          type="text"
          value={subtitle}
          onChange={(e) => setSubtitle(e.target.value)}
          placeholder="Subtitulo (opcional)"
          className={inputClass}
        />
      </div>

      {/* Author Name */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Autor
        </label>
        <input
          type="text"
          value={authorName}
          onChange={(e) => setAuthorName(e.target.value)}
          placeholder="Nome do autor (opcional)"
          maxLength={255}
          className={inputClass}
        />
      </div>

      {/* Content Type */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Tipo
        </label>
        <select
          value={contentType}
          onChange={(e) => setContentType(e.target.value)}
          className={inputClass}
        >
          {CONTENT_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>
              {ct.label}
            </option>
          ))}
        </select>
      </div>

      {/* Body (Markdown Editor) */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Conteudo (Markdown) *
        </label>
        <div data-color-mode="dark">
          <MDEditor
            value={bodyMd}
            onChange={(val) => setBodyMd(val ?? "")}
            height={400}
            preview="live"
          />
        </div>
      </div>

      {/* Summary */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Resumo
        </label>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="Resumo curto para cards e listagens"
          rows={2}
          className={inputClass}
        />
      </div>

      {/* Meta Description */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Meta Description (SEO)
        </label>
        <textarea
          value={metaDescription}
          onChange={(e) => setMetaDescription(e.target.value)}
          placeholder="Descricao para SEO (max 320 caracteres)"
          rows={2}
          maxLength={320}
          className={inputClass}
        />
        <p className="mt-1 text-right font-mono text-[11px] text-ash">
          {metaDescription.length}/320
        </p>
      </div>

      {/* Sources */}
      <div>
        <label className="mb-1 block font-mono text-[11px] uppercase tracking-[1px] text-ash">
          Fontes
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={newSource}
            onChange={(e) => setNewSource(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSource())}
            placeholder="https://..."
            className={inputClass}
          />
          <button
            type="button"
            onClick={addSource}
            className="shrink-0 rounded-lg border border-[rgba(255,255,255,0.1)] px-3 py-2 font-mono text-[12px] text-ash transition-colors hover:border-signal hover:text-signal"
          >
            Adicionar
          </button>
        </div>
        {sources.length > 0 && (
          <ul className="mt-2 space-y-1">
            {sources.map((src, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded-md bg-[rgba(255,255,255,0.04)] px-3 py-1.5"
              >
                <span className="truncate font-mono text-[12px] text-bone">{src}</span>
                <button
                  onClick={() => removeSource(i)}
                  className="ml-2 font-mono text-[11px] text-ash hover:text-[#FF5959]"
                >
                  x
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 border-t border-[rgba(255,255,255,0.06)] pt-6">
        <button
          onClick={() => onSave(getData())}
          disabled={saving || !title || !bodyMd}
          className="rounded-lg border border-[rgba(255,255,255,0.1)] px-5 py-2.5 font-mono text-[13px] font-semibold text-bone transition-colors hover:border-bone disabled:opacity-40"
        >
          {saving ? "Salvando..." : "Salvar rascunho"}
        </button>
        {onPublish && (
          <button
            onClick={() => onPublish(getData())}
            disabled={saving || !title || !bodyMd}
            className="rounded-lg bg-signal px-5 py-2.5 font-mono text-[13px] font-semibold text-sinal-black transition-colors hover:bg-signal-dim disabled:opacity-40"
          >
            {saving ? "Publicando..." : "Publicar"}
          </button>
        )}
      </div>
    </div>
  );
}
