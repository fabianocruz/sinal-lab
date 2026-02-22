"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ContentEditor, { type ContentEditorData } from "@/components/admin/ContentEditor";
import { adminGetContent, adminUpdateContent, type AdminContent } from "@/lib/admin-api";

export default function EditContentPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [content, setContent] = useState<AdminContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await adminGetContent(params.slug);
        setContent(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar conteudo");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.slug]);

  async function handleSave(data: ContentEditorData) {
    setSaving(true);
    try {
      await adminUpdateContent(params.slug, {
        title: data.title,
        subtitle: data.subtitle || undefined,
        body_md: data.body_md,
        content_type: data.content_type,
        summary: data.summary || undefined,
        meta_description: data.meta_description || undefined,
        sources: data.sources.length > 0 ? data.sources : undefined,
        author_name: data.author_name || undefined,
      });
      router.push("/admin/content");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="py-8 font-mono text-[13px] text-ash">Carregando...</p>;
  }

  if (error || !content) {
    return (
      <p className="py-8 font-mono text-[13px] text-[#FF5959]">
        {error ?? "Conteudo nao encontrado."}
      </p>
    );
  }

  return (
    <div>
      <h1 className="mb-6 font-display text-[28px] text-sinal-white">Editar conteudo</h1>
      <ContentEditor
        initialData={{
          title: content.title,
          subtitle: content.subtitle ?? "",
          body_md: content.body_md,
          content_type: content.content_type,
          summary: "",
          meta_description: content.meta_description ?? "",
          sources: content.sources ?? [],
          author_name: content.author_name ?? "",
        }}
        onSave={handleSave}
        saving={saving}
      />
    </div>
  );
}
