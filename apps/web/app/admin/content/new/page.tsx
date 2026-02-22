"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ContentEditor, { type ContentEditorData } from "@/components/admin/ContentEditor";
import { adminCreateContent, adminPublishContent } from "@/lib/admin-api";

export default function NewContentPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function handleSave(data: ContentEditorData) {
    setSaving(true);
    try {
      await adminCreateContent({
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

  async function handlePublish(data: ContentEditorData) {
    setSaving(true);
    try {
      const created = await adminCreateContent({
        title: data.title,
        subtitle: data.subtitle || undefined,
        body_md: data.body_md,
        content_type: data.content_type,
        summary: data.summary || undefined,
        meta_description: data.meta_description || undefined,
        sources: data.sources.length > 0 ? data.sources : undefined,
        author_name: data.author_name || undefined,
      });
      await adminPublishContent(created.slug);
      router.push("/admin/content");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao publicar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 font-display text-[28px] text-sinal-white">Novo conteudo</h1>
      <ContentEditor onSave={handleSave} onPublish={handlePublish} saving={saving} />
    </div>
  );
}
