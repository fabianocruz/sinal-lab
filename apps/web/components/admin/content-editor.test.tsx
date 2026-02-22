import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mock @uiw/react-md-editor — the real package uses browser APIs unavailable
// in jsdom. We replace it with a plain controlled textarea so tests can read
// and set the body_md field via data-testid="md-editor".
// ---------------------------------------------------------------------------
// MockMDEditor is shared between the @uiw/react-md-editor mock and the
// next/dynamic mock so both resolve to exactly the same component.
// It renders a textarea for normal text input and a hidden button that
// calls onChange(undefined) — covering the `val ?? ""` null-coalescing
// branch inside ContentEditor that fires when the real editor clears.
function MockMDEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (val: string | undefined) => void;
}) {
  return (
    <>
      <textarea data-testid="md-editor" value={value} onChange={(e) => onChange(e.target.value)} />
      <button
        type="button"
        data-testid="md-editor-clear"
        onClick={() => onChange(undefined)}
        style={{ display: "none" }}
      >
        clear
      </button>
    </>
  );
}
MockMDEditor.displayName = "MDEditor";

vi.mock("@uiw/react-md-editor", () => ({
  default: MockMDEditor,
}));

// ---------------------------------------------------------------------------
// Mock next/dynamic — the real implementation defers to a lazy import that
// resolves asynchronously. We unwrap it immediately so the MDEditor mock
// above is rendered synchronously during tests.
// ---------------------------------------------------------------------------
vi.mock("next/dynamic", () => ({
  default: (_loader: () => Promise<unknown>, _opts?: Record<string, unknown>) => MockMDEditor,
}));

// Import AFTER mocks are registered so the module picks them up.
import ContentEditor, { ContentEditorData } from "./ContentEditor";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderEditor(props: Partial<React.ComponentProps<typeof ContentEditor>> = {}) {
  const onSave = props.onSave ?? vi.fn().mockResolvedValue(undefined);
  const result = render(<ContentEditor onSave={onSave} {...props} />);
  return { ...result, onSave };
}

function getTitleInput() {
  return screen.getByPlaceholderText("Titulo do conteudo");
}

function getBodyEditor() {
  return screen.getByTestId("md-editor");
}

function getSaveButton() {
  return screen.getByRole("button", { name: /Salvar rascunho/i });
}

function getPublishButton() {
  return screen.getByRole("button", { name: /Publicar/i });
}

// ===========================================================================
// ContentEditor
// ===========================================================================

describe("ContentEditor", () => {
  // -------------------------------------------------------------------------
  // Structure / rendering
  // -------------------------------------------------------------------------

  describe("structure", () => {
    it("test_contenteditor_renders_without_crash", () => {
      renderEditor();
      expect(screen.getByPlaceholderText("Titulo do conteudo")).toBeInTheDocument();
    });

    it("test_contenteditor_shows_title_input", () => {
      renderEditor();
      expect(getTitleInput()).toBeInTheDocument();
    });

    it("test_contenteditor_shows_subtitle_input", () => {
      renderEditor();
      expect(screen.getByPlaceholderText("Subtitulo (opcional)")).toBeInTheDocument();
    });

    it("test_contenteditor_shows_content_type_select_with_all_options", () => {
      renderEditor();
      const select = screen.getByDisplayValue("Artigo");
      expect(select).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Artigo" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Post" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "How-to" })).toBeInTheDocument();
    });

    it("test_contenteditor_shows_markdown_editor", () => {
      renderEditor();
      expect(getBodyEditor()).toBeInTheDocument();
    });

    it("test_contenteditor_shows_summary_textarea", () => {
      renderEditor();
      expect(
        screen.getByPlaceholderText("Resumo curto para cards e listagens"),
      ).toBeInTheDocument();
    });

    it("test_contenteditor_shows_meta_description_textarea", () => {
      renderEditor();
      expect(
        screen.getByPlaceholderText("Descricao para SEO (max 320 caracteres)"),
      ).toBeInTheDocument();
    });

    it("test_contenteditor_shows_salvar_rascunho_button", () => {
      renderEditor();
      expect(getSaveButton()).toBeInTheDocument();
    });

    it("test_contenteditor_does_not_show_publicar_button_when_onpublish_is_not_provided", () => {
      renderEditor();
      expect(screen.queryByRole("button", { name: /Publicar/i })).not.toBeInTheDocument();
    });

    it("test_contenteditor_shows_publicar_button_when_onpublish_is_provided", () => {
      renderEditor({ onPublish: vi.fn().mockResolvedValue(undefined) });
      expect(getPublishButton()).toBeInTheDocument();
    });

    it("test_contenteditor_shows_adicionar_button_for_sources", () => {
      renderEditor();
      expect(screen.getByRole("button", { name: "Adicionar" })).toBeInTheDocument();
    });

    it("test_contenteditor_shows_source_url_input", () => {
      renderEditor();
      expect(screen.getByPlaceholderText("https://...")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Slug auto-generation
  // -------------------------------------------------------------------------

  describe("slug auto-generation", () => {
    it("test_contenteditor_shows_slug_when_title_is_typed", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Hello World" } });
      expect(screen.getByText("hello-world")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_portuguese_accents", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Análise técnica" } });
      expect(screen.getByText("analise-tecnica")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_cedilla", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Informação básica" } });
      expect(screen.getByText("informacao-basica")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_multiple_spaces", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Hello   World" } });
      expect(screen.getByText("hello-world")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_special_characters", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Hello & World!" } });
      expect(screen.getByText("hello-world")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_strips_leading_and_trailing_hyphens", () => {
      renderEditor();
      // A title of only special chars produces an empty slug, so test
      // a title that would produce leading/trailing hyphens via spacing
      fireEvent.change(getTitleInput(), { target: { value: "  Hello  " } });
      expect(screen.getByText("hello")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_is_not_shown_when_title_is_empty", () => {
      renderEditor();
      // No title typed — slug paragraph should not appear
      expect(screen.queryByText(/Slug:/)).not.toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_all_accent_families", () => {
      renderEditor();
      // à→a, è→e, ì→i, ò→o, ù→u, ñ→n, ç→c  |  Á→a, É→e, Í→i, Ó→o, Ú→u
      fireEvent.change(getTitleInput(), {
        target: { value: "àèìòùñç ÁÉÍÓÚ" },
      });
      expect(screen.getByText("aeiounc-aeiou")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_handles_all_accents_correctly", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "ñoño çiçek" } });
      expect(screen.getByText("nono-cicek")).toBeInTheDocument();
    });

    it("test_contenteditor_slug_uses_current_title_from_initial_data", () => {
      renderEditor({ initialData: { title: "Meu Artigo" } });
      expect(screen.getByText("meu-artigo")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Initial data
  // -------------------------------------------------------------------------

  describe("initial data", () => {
    const initialData: Partial<ContentEditorData> = {
      title: "Titulo inicial",
      subtitle: "Subtitulo inicial",
      body_md: "Conteudo inicial",
      content_type: "POST",
      summary: "Resumo inicial",
      meta_description: "Descricao SEO inicial",
      sources: ["https://exemplo.com"],
    };

    it("test_contenteditor_prefills_title_from_initial_data", () => {
      renderEditor({ initialData });
      expect(getTitleInput()).toHaveValue("Titulo inicial");
    });

    it("test_contenteditor_prefills_subtitle_from_initial_data", () => {
      renderEditor({ initialData });
      expect(screen.getByPlaceholderText("Subtitulo (opcional)")).toHaveValue("Subtitulo inicial");
    });

    it("test_contenteditor_prefills_body_md_from_initial_data", () => {
      renderEditor({ initialData });
      expect(getBodyEditor()).toHaveValue("Conteudo inicial");
    });

    it("test_contenteditor_prefills_content_type_from_initial_data", () => {
      renderEditor({ initialData });
      expect(screen.getByDisplayValue("Post")).toBeInTheDocument();
    });

    it("test_contenteditor_prefills_summary_from_initial_data", () => {
      renderEditor({ initialData });
      expect(screen.getByPlaceholderText("Resumo curto para cards e listagens")).toHaveValue(
        "Resumo inicial",
      );
    });

    it("test_contenteditor_prefills_meta_description_from_initial_data", () => {
      renderEditor({ initialData });
      expect(screen.getByPlaceholderText("Descricao para SEO (max 320 caracteres)")).toHaveValue(
        "Descricao SEO inicial",
      );
    });

    it("test_contenteditor_prefills_sources_from_initial_data", () => {
      renderEditor({ initialData });
      expect(screen.getByText("https://exemplo.com")).toBeInTheDocument();
    });

    it("test_contenteditor_defaults_to_article_content_type_when_not_provided", () => {
      renderEditor({ initialData: {} });
      expect(screen.getByDisplayValue("Artigo")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Required fields / disabled state
  // -------------------------------------------------------------------------

  describe("required fields and disabled state", () => {
    it("test_contenteditor_save_button_is_disabled_when_title_is_empty", () => {
      renderEditor();
      // body_md is also empty by default
      expect(getSaveButton()).toBeDisabled();
    });

    it("test_contenteditor_save_button_is_disabled_when_body_md_is_empty", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      // body_md still empty
      expect(getSaveButton()).toBeDisabled();
    });

    it("test_contenteditor_save_button_is_disabled_when_title_is_empty_but_body_has_content", () => {
      renderEditor();
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });
      // title still empty
      expect(getSaveButton()).toBeDisabled();
    });

    it("test_contenteditor_save_button_is_enabled_when_title_and_body_have_content", () => {
      renderEditor();
      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });
      expect(getSaveButton()).not.toBeDisabled();
    });

    it("test_contenteditor_publish_button_is_disabled_when_title_is_empty", () => {
      renderEditor({ onPublish: vi.fn().mockResolvedValue(undefined) });
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });
      expect(getPublishButton()).toBeDisabled();
    });

    it("test_contenteditor_publish_button_is_disabled_when_body_md_is_empty", () => {
      renderEditor({ onPublish: vi.fn().mockResolvedValue(undefined) });
      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      expect(getPublishButton()).toBeDisabled();
    });

    it("test_contenteditor_publish_button_is_enabled_when_title_and_body_have_content", () => {
      renderEditor({ onPublish: vi.fn().mockResolvedValue(undefined) });
      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });
      expect(getPublishButton()).not.toBeDisabled();
    });

    it("test_contenteditor_both_buttons_enabled_when_initial_data_has_title_and_body", () => {
      renderEditor({
        initialData: { title: "Titulo", body_md: "Conteudo" },
        onPublish: vi.fn().mockResolvedValue(undefined),
      });
      expect(getSaveButton()).not.toBeDisabled();
      expect(getPublishButton()).not.toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // Saving state
  // -------------------------------------------------------------------------

  describe("saving state", () => {
    it("test_contenteditor_shows_salvando_text_when_saving_is_true", () => {
      renderEditor({
        saving: true,
        initialData: { title: "Titulo", body_md: "Conteudo" },
      });
      expect(screen.getByRole("button", { name: "Salvando..." })).toBeInTheDocument();
    });

    it("test_contenteditor_shows_publicando_text_when_saving_is_true_and_onpublish_exists", () => {
      renderEditor({
        saving: true,
        initialData: { title: "Titulo", body_md: "Conteudo" },
        onPublish: vi.fn().mockResolvedValue(undefined),
      });
      expect(screen.getByRole("button", { name: "Publicando..." })).toBeInTheDocument();
    });

    it("test_contenteditor_save_button_is_disabled_when_saving_is_true", () => {
      renderEditor({
        saving: true,
        initialData: { title: "Titulo", body_md: "Conteudo" },
      });
      expect(screen.getByRole("button", { name: "Salvando..." })).toBeDisabled();
    });

    it("test_contenteditor_publish_button_is_disabled_when_saving_is_true", () => {
      renderEditor({
        saving: true,
        initialData: { title: "Titulo", body_md: "Conteudo" },
        onPublish: vi.fn().mockResolvedValue(undefined),
      });
      expect(screen.getByRole("button", { name: "Publicando..." })).toBeDisabled();
    });

    it("test_contenteditor_shows_salvar_rascunho_text_when_saving_is_false", () => {
      renderEditor({
        saving: false,
        initialData: { title: "Titulo", body_md: "Conteudo" },
      });
      expect(getSaveButton()).toHaveTextContent("Salvar rascunho");
    });

    it("test_contenteditor_shows_publicar_text_when_saving_is_false_and_onpublish_exists", () => {
      renderEditor({
        saving: false,
        initialData: { title: "Titulo", body_md: "Conteudo" },
        onPublish: vi.fn().mockResolvedValue(undefined),
      });
      expect(getPublishButton()).toHaveTextContent("Publicar");
    });
  });

  // -------------------------------------------------------------------------
  // Sources management
  // -------------------------------------------------------------------------

  describe("sources management", () => {
    function getSourceInput() {
      return screen.getByPlaceholderText("https://...");
    }

    function getAdicionarButton() {
      return screen.getByRole("button", { name: "Adicionar" });
    }

    it("test_contenteditor_can_add_a_source_url", () => {
      renderEditor();
      fireEvent.change(getSourceInput(), {
        target: { value: "https://exemplo.com" },
      });
      fireEvent.click(getAdicionarButton());
      expect(screen.getByText("https://exemplo.com")).toBeInTheDocument();
    });

    it("test_contenteditor_clears_source_input_after_adding", () => {
      renderEditor();
      fireEvent.change(getSourceInput(), {
        target: { value: "https://exemplo.com" },
      });
      fireEvent.click(getAdicionarButton());
      expect(getSourceInput()).toHaveValue("");
    });

    it("test_contenteditor_can_remove_a_source_url", () => {
      renderEditor({ initialData: { sources: ["https://exemplo.com"] } });
      expect(screen.getByText("https://exemplo.com")).toBeInTheDocument();

      const removeButton = screen.getByRole("button", { name: "x" });
      fireEvent.click(removeButton);

      expect(screen.queryByText("https://exemplo.com")).not.toBeInTheDocument();
    });

    it("test_contenteditor_does_not_add_duplicate_sources", () => {
      renderEditor({ initialData: { sources: ["https://exemplo.com"] } });
      fireEvent.change(getSourceInput(), {
        target: { value: "https://exemplo.com" },
      });
      fireEvent.click(getAdicionarButton());

      const items = screen.getAllByText("https://exemplo.com");
      expect(items).toHaveLength(1);
    });

    it("test_contenteditor_does_not_add_empty_source", () => {
      renderEditor();
      // Input is empty — clicking Adicionar should not render any source item
      fireEvent.click(getAdicionarButton());
      expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
    });

    it("test_contenteditor_does_not_add_whitespace_only_source", () => {
      renderEditor();
      fireEvent.change(getSourceInput(), { target: { value: "   " } });
      fireEvent.click(getAdicionarButton());
      expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
    });

    it("test_contenteditor_can_add_multiple_sources", () => {
      renderEditor();
      const urls = ["https://primeiro.com", "https://segundo.com", "https://terceiro.com"];
      urls.forEach((url) => {
        fireEvent.change(getSourceInput(), { target: { value: url } });
        fireEvent.click(getAdicionarButton());
      });
      urls.forEach((url) => {
        expect(screen.getByText(url)).toBeInTheDocument();
      });
    });

    it("test_contenteditor_can_remove_one_source_from_multiple", () => {
      renderEditor({
        initialData: { sources: ["https://primeiro.com", "https://segundo.com"] },
      });
      const removeButtons = screen.getAllByRole("button", { name: "x" });
      fireEvent.click(removeButtons[0]);

      expect(screen.queryByText("https://primeiro.com")).not.toBeInTheDocument();
      expect(screen.getByText("https://segundo.com")).toBeInTheDocument();
    });

    it("test_contenteditor_can_add_source_by_pressing_enter", () => {
      renderEditor();
      fireEvent.change(getSourceInput(), {
        target: { value: "https://enter-source.com" },
      });
      fireEvent.keyDown(getSourceInput(), { key: "Enter" });
      expect(screen.getByText("https://enter-source.com")).toBeInTheDocument();
    });

    it("test_contenteditor_does_not_submit_form_on_enter_in_source_input", () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      render(<ContentEditor onSave={onSave} />);
      fireEvent.change(getSourceInput(), {
        target: { value: "https://exemplo.com" },
      });
      fireEvent.keyDown(getSourceInput(), { key: "Enter" });
      // onSave should NOT have been called — Enter only adds the source
      expect(onSave).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Callbacks
  // -------------------------------------------------------------------------

  describe("callbacks", () => {
    it("test_contenteditor_calls_onsave_with_correct_data_when_salvar_is_clicked", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      render(<ContentEditor onSave={onSave} initialData={{ sources: ["https://fonte.com"] }} />);

      fireEvent.change(getTitleInput(), { target: { value: "Meu titulo" } });
      fireEvent.change(screen.getByPlaceholderText("Subtitulo (opcional)"), {
        target: { value: "Meu subtitulo" },
      });
      fireEvent.change(getBodyEditor(), { target: { value: "# Conteudo" } });
      fireEvent.change(screen.getByPlaceholderText("Resumo curto para cards e listagens"), {
        target: { value: "Resumo aqui" },
      });
      fireEvent.change(screen.getByPlaceholderText("Descricao para SEO (max 320 caracteres)"), {
        target: { value: "Meta desc" },
      });

      fireEvent.click(getSaveButton());

      await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
      expect(onSave).toHaveBeenCalledWith({
        title: "Meu titulo",
        subtitle: "Meu subtitulo",
        body_md: "# Conteudo",
        content_type: "ARTICLE",
        summary: "Resumo aqui",
        meta_description: "Meta desc",
        sources: ["https://fonte.com"],
        author_name: "",
      });
    });

    it("test_contenteditor_calls_onpublish_with_correct_data_when_publicar_is_clicked", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const onPublish = vi.fn().mockResolvedValue(undefined);
      render(
        <ContentEditor
          onSave={onSave}
          onPublish={onPublish}
          initialData={{ title: "Publicavel", body_md: "Corpo" }}
        />,
      );

      fireEvent.click(getPublishButton());

      await waitFor(() => expect(onPublish).toHaveBeenCalledTimes(1));
      expect(onPublish).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Publicavel",
          body_md: "Corpo",
        }),
      );
      // onSave must NOT be called when Publicar is clicked
      expect(onSave).not.toHaveBeenCalled();
    });

    it("test_contenteditor_calls_onsave_with_updated_content_type", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      render(<ContentEditor onSave={onSave} />);

      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });
      fireEvent.change(screen.getByDisplayValue("Artigo"), {
        target: { value: "HOWTO" },
      });

      fireEvent.click(getSaveButton());

      await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ content_type: "HOWTO" }));
    });

    it("test_contenteditor_calls_onsave_with_all_added_sources", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      render(<ContentEditor onSave={onSave} />);

      fireEvent.change(getTitleInput(), { target: { value: "Titulo" } });
      fireEvent.change(getBodyEditor(), { target: { value: "Conteudo" } });

      const sourceInput = screen.getByPlaceholderText("https://...");
      fireEvent.change(sourceInput, { target: { value: "https://a.com" } });
      fireEvent.click(screen.getByRole("button", { name: "Adicionar" }));
      fireEvent.change(sourceInput, { target: { value: "https://b.com" } });
      fireEvent.click(screen.getByRole("button", { name: "Adicionar" }));

      fireEvent.click(getSaveButton());

      await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ sources: ["https://a.com", "https://b.com"] }),
      );
    });

    it("test_contenteditor_onsave_not_called_when_button_is_disabled", () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      render(<ContentEditor onSave={onSave} />);
      // title and body are empty — button is disabled
      fireEvent.click(getSaveButton());
      expect(onSave).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Meta description character counter
  // -------------------------------------------------------------------------

  describe("meta description character counter", () => {
    function getMetaTextarea() {
      return screen.getByPlaceholderText("Descricao para SEO (max 320 caracteres)");
    }

    it("test_contenteditor_shows_character_counter_starting_at_zero", () => {
      renderEditor();
      expect(screen.getByText("0/320")).toBeInTheDocument();
    });

    it("test_contenteditor_counter_updates_as_text_is_typed", () => {
      renderEditor();
      fireEvent.change(getMetaTextarea(), { target: { value: "Ola mundo" } });
      expect(screen.getByText("9/320")).toBeInTheDocument();
    });

    it("test_contenteditor_counter_reflects_initial_data_length", () => {
      const meta = "A".repeat(50);
      renderEditor({ initialData: { meta_description: meta } });
      expect(screen.getByText("50/320")).toBeInTheDocument();
    });

    it("test_contenteditor_counter_shows_maximum_at_320_characters", () => {
      renderEditor();
      const longText = "x".repeat(320);
      fireEvent.change(getMetaTextarea(), { target: { value: longText } });
      expect(screen.getByText("320/320")).toBeInTheDocument();
    });

    it("test_contenteditor_meta_description_has_maxlength_attribute_of_320", () => {
      renderEditor();
      expect(getMetaTextarea()).toHaveAttribute("maxLength", "320");
    });

    it("test_contenteditor_counter_resets_to_zero_when_text_is_cleared", () => {
      renderEditor();
      fireEvent.change(getMetaTextarea(), { target: { value: "Texto" } });
      expect(screen.getByText("5/320")).toBeInTheDocument();

      fireEvent.change(getMetaTextarea(), { target: { value: "" } });
      expect(screen.getByText("0/320")).toBeInTheDocument();
    });

    it("test_contenteditor_counter_handles_unicode_characters", () => {
      renderEditor();
      // Each emoji or accented char counts as one character in .length
      fireEvent.change(getMetaTextarea(), { target: { value: "ção" } });
      expect(screen.getByText("3/320")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe("edge cases", () => {
    it("test_contenteditor_handles_empty_initial_data_object", () => {
      renderEditor({ initialData: {} });
      expect(getTitleInput()).toHaveValue("");
      expect(getBodyEditor()).toHaveValue("");
    });

    it("test_contenteditor_handles_undefined_initial_data", () => {
      renderEditor({ initialData: undefined });
      expect(getTitleInput()).toHaveValue("");
    });

    it("test_contenteditor_slug_label_is_shown_only_when_slug_is_non_empty", () => {
      renderEditor();
      // Empty title → no slug display
      expect(screen.queryByText(/Slug:/)).not.toBeInTheDocument();

      fireEvent.change(getTitleInput(), { target: { value: "Algo" } });
      expect(screen.getByText(/Slug:/)).toBeInTheDocument();

      // Clear title again
      fireEvent.change(getTitleInput(), { target: { value: "" } });
      expect(screen.queryByText(/Slug:/)).not.toBeInTheDocument();
    });

    it("test_contenteditor_slug_from_title_with_only_special_chars_produces_no_slug", () => {
      renderEditor();
      // "!!!" → slugify → "" → slug display should not appear
      fireEvent.change(getTitleInput(), { target: { value: "!!!" } });
      expect(screen.queryByText(/Slug:/)).not.toBeInTheDocument();
    });

    it("test_contenteditor_source_list_not_rendered_when_sources_are_empty", () => {
      renderEditor();
      expect(screen.queryByRole("list")).not.toBeInTheDocument();
    });

    it("test_contenteditor_source_list_disappears_after_all_sources_are_removed", () => {
      renderEditor({ initialData: { sources: ["https://unico.com"] } });
      expect(screen.getByRole("list")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "x" }));
      expect(screen.queryByRole("list")).not.toBeInTheDocument();
    });

    it("test_contenteditor_body_md_falls_back_to_empty_string_when_editor_returns_undefined", () => {
      // Covers the `val ?? ""` null-coalescing branch in ContentEditor line 157.
      // The real @uiw/react-md-editor calls onChange(undefined) when the
      // editor content is programmatically cleared.
      renderEditor({ initialData: { title: "T", body_md: "Inicial" } });
      // Verify body has content so the save button is enabled
      expect(getSaveButton()).not.toBeDisabled();

      // Trigger onChange(undefined) via the hidden clear button on the mock
      fireEvent.click(screen.getByTestId("md-editor-clear"));

      // body_md is now "" so the save button must become disabled
      expect(getSaveButton()).toBeDisabled();
    });
  });
});
