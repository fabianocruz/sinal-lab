import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import HeroImage from "@/components/newsletter/HeroImage";
import VideoEmbed from "@/components/newsletter/VideoEmbed";
import CalloutBox from "@/components/newsletter/CalloutBox";
import ReadingTime from "@/components/newsletter/ReadingTime";
import type { HeroImage as HeroImageType, FeaturedVideo, Callout } from "@/lib/newsletter";

// ---------------------------------------------------------------------------
// HeroImage
// ---------------------------------------------------------------------------

describe("HeroImage — rendering", () => {
  it("test_heroimage_with_url_renders_img_element", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "A test image",
    };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    const img = screen.getByRole("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/photo.jpg");
    expect(img).toHaveAttribute("alt", "A test image");
  });

  it("test_heroimage_with_caption_shows_caption_text", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "",
      caption: "Foto tirada em Sao Paulo, fevereiro 2026",
    };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(screen.getByText("Foto tirada em Sao Paulo, fevereiro 2026")).toBeInTheDocument();
  });

  it("test_heroimage_with_credit_shows_credit_text", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "",
      credit: "Foto: Reuters",
    };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(screen.getByText("Foto: Reuters")).toBeInTheDocument();
  });

  it("test_heroimage_with_caption_and_credit_shows_both", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "Alt text",
      caption: "Legenda da imagem",
      credit: "Credito: AP",
    };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(screen.getByText("Legenda da imagem")).toBeInTheDocument();
    expect(screen.getByText("Credito: AP")).toBeInTheDocument();
  });

  it("test_heroimage_null_returns_nothing", () => {
    const { container } = render(<HeroImage hero_image={null} agentColor="#E8FF59" />);

    expect(container.innerHTML).toBe("");
  });

  it("test_heroimage_empty_url_returns_nothing", () => {
    const hero: HeroImageType = {
      url: "",
      alt: "empty url",
    };

    const { container } = render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(container.innerHTML).toBe("");
  });

  it("test_heroimage_undefined_returns_nothing", () => {
    const { container } = render(<HeroImage hero_image={undefined} agentColor="#E8FF59" />);

    expect(container.innerHTML).toBe("");
  });

  it("test_heroimage_without_caption_or_credit_omits_figcaption", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "No caption or credit",
    };

    const { container } = render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(container.querySelector("figcaption")).not.toBeInTheDocument();
  });
});

describe("HeroImage — edge cases", () => {
  it("test_heroimage_missing_alt_defaults_to_empty_string", () => {
    const hero: HeroImageType = { url: "https://example.com/photo.jpg" };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("alt", "");
  });

  it("test_heroimage_with_only_credit_no_caption_shows_credit", () => {
    const hero: HeroImageType = {
      url: "https://example.com/photo.jpg",
      alt: "",
      credit: "Reuters",
    };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    expect(screen.getByText("Reuters")).toBeInTheDocument();
    expect(screen.queryByText("undefined")).not.toBeInTheDocument();
  });

  it("test_heroimage_uses_eager_loading", () => {
    const hero: HeroImageType = { url: "https://cdn.example.com/img.webp", alt: "hero" };

    render(<HeroImage hero_image={hero} agentColor="#E8FF59" />);

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("loading", "eager");
  });
});

// ---------------------------------------------------------------------------
// VideoEmbed
// ---------------------------------------------------------------------------

describe("VideoEmbed — YouTube", () => {
  it("test_videoembed_youtube_watch_url_renders_iframe", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ");
  });

  it("test_videoembed_youtu_be_short_url_renders_iframe", () => {
    const video: FeaturedVideo = {
      url: "https://youtu.be/dQw4w9WgXcQ",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ");
  });

  it("test_videoembed_youtube_uses_privacy_enhanced_nocookie_domain", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=abc123",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe?.getAttribute("src")).toContain("youtube-nocookie.com");
  });
});

describe("VideoEmbed — Vimeo", () => {
  it("test_videoembed_vimeo_url_renders_iframe", () => {
    const video: FeaturedVideo = {
      url: "https://vimeo.com/123456789",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("src", "https://player.vimeo.com/video/123456789");
  });

  it("test_videoembed_vimeo_uses_player_subdomain", () => {
    const video: FeaturedVideo = {
      url: "https://vimeo.com/987654321",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe?.getAttribute("src")).toContain("player.vimeo.com/video/987654321");
  });
});

describe("VideoEmbed — caption", () => {
  it("test_videoembed_with_caption_shows_caption_text", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      caption: "Apresentacao da startup no Demo Day",
    };

    render(<VideoEmbed video={video} />);

    expect(screen.getByText("Apresentacao da startup no Demo Day")).toBeInTheDocument();
  });

  it("test_videoembed_without_caption_omits_figcaption", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    };

    const { container } = render(<VideoEmbed video={video} />);

    expect(container.querySelector("figcaption")).not.toBeInTheDocument();
  });
});

describe("VideoEmbed — edge cases", () => {
  it("test_videoembed_youtube_url_with_extra_params_still_extracts_id", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=abc123&t=42&list=PLxyz",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/abc123");
  });

  it("test_videoembed_with_title_uses_title_in_iframe", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      title: "Demo Day Presentation",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("title", "Demo Day Presentation");
  });

  it("test_videoembed_without_title_defaults_to_video", () => {
    const video: FeaturedVideo = {
      url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("title", "Video");
  });

  it("test_videoembed_empty_url_returns_nothing", () => {
    const video: FeaturedVideo = { url: "" };

    const { container } = render(<VideoEmbed video={video} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_videoembed_iframe_has_allowfullscreen", () => {
    const video: FeaturedVideo = { url: "https://vimeo.com/111222333" };

    const { container } = render(<VideoEmbed video={video} />);

    const iframe = container.querySelector("iframe");
    expect(iframe).toHaveAttribute("allowfullscreen");
  });
});

describe("VideoEmbed — null and unrecognized URLs", () => {
  it("test_videoembed_null_returns_nothing", () => {
    const { container } = render(<VideoEmbed video={null} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_videoembed_undefined_returns_nothing", () => {
    const { container } = render(<VideoEmbed video={undefined} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_videoembed_unrecognized_url_returns_nothing", () => {
    const video: FeaturedVideo = {
      url: "https://dailymotion.com/video/x7xyz",
    };

    const { container } = render(<VideoEmbed video={video} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_videoembed_plain_text_url_returns_nothing", () => {
    const video: FeaturedVideo = {
      url: "not-a-url-at-all",
    };

    const { container } = render(<VideoEmbed video={video} />);

    expect(container.innerHTML).toBe("");
  });
});

// ---------------------------------------------------------------------------
// CalloutBox
// ---------------------------------------------------------------------------

describe("CalloutBox — content", () => {
  it("test_calloutbox_shows_content_text", () => {
    const callout: Callout = {
      type: "highlight",
      content: "Este e um destaque importante para o leitor.",
      position: "after_intro",
    };

    render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(screen.getByText("Este e um destaque importante para o leitor.")).toBeInTheDocument();
  });
});

describe("CalloutBox — border colors", () => {
  it("test_calloutbox_highlight_type_uses_agent_color_for_border", () => {
    const callout: Callout = {
      type: "highlight",
      content: "Conteudo destaque.",
      position: "after_intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#59FFB4" />);

    const aside = container.querySelector("aside");
    expect(aside).toHaveStyle({ borderColor: "#59FFB4" });
  });

  it("test_calloutbox_highlight_type_label_color_matches_agent_color", () => {
    const callout: Callout = {
      type: "highlight",
      content: "Conteudo.",
      position: "after_intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#59FFB4" />);

    const label = container.querySelector("span");
    expect(label).toHaveStyle({ color: "#59FFB4" });
  });

  it("test_calloutbox_note_type_uses_blue_border", () => {
    const callout: Callout = {
      type: "note",
      content: "Uma nota tecnica relevante.",
      position: "after_intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    const aside = container.querySelector("aside");
    expect(aside).toHaveStyle({ borderColor: "#59B4FF" });
  });

  it("test_calloutbox_warning_type_uses_amber_border", () => {
    const callout: Callout = {
      type: "warning",
      content: "Atencao a este ponto.",
      position: "after_intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    const aside = container.querySelector("aside");
    expect(aside).toHaveStyle({ borderColor: "#FFB459" });
  });

  it("test_calloutbox_note_type_ignores_agent_color", () => {
    // The agent color must NOT bleed into non-highlight types.
    const callout: Callout = {
      type: "note",
      content: "Nota.",
      position: "intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#FF8A59" />);

    const aside = container.querySelector("aside");
    // border must be the fixed blue, not the orange agent color
    expect(aside).toHaveStyle({ borderColor: "#59B4FF" });
    expect(aside).not.toHaveStyle({ borderColor: "#FF8A59" });
  });

  it("test_calloutbox_warning_type_ignores_agent_color", () => {
    const callout: Callout = {
      type: "warning",
      content: "Aviso.",
      position: "intro",
    };

    const { container } = render(<CalloutBox callout={callout} agentColor="#C459FF" />);

    const aside = container.querySelector("aside");
    expect(aside).toHaveStyle({ borderColor: "#FFB459" });
    expect(aside).not.toHaveStyle({ borderColor: "#C459FF" });
  });
});

describe("CalloutBox — labels", () => {
  it("test_calloutbox_highlight_type_shows_destaque_label", () => {
    const callout: Callout = {
      type: "highlight",
      content: "Conteudo.",
      position: "intro",
    };

    render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(screen.getByText("DESTAQUE")).toBeInTheDocument();
  });

  it("test_calloutbox_note_type_shows_nota_label", () => {
    const callout: Callout = {
      type: "note",
      content: "Conteudo.",
      position: "intro",
    };

    render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(screen.getByText("NOTA")).toBeInTheDocument();
  });

  it("test_calloutbox_warning_type_shows_atencao_label", () => {
    const callout: Callout = {
      type: "warning",
      content: "Conteudo.",
      position: "intro",
    };

    render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(screen.getByText("ATENCAO")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ReadingTime
// ---------------------------------------------------------------------------

describe("ReadingTime — rendering", () => {
  it("test_readingtime_with_minutes_shows_minutes_text", () => {
    render(<ReadingTime minutes={5} />);

    expect(screen.getByText("5 min de leitura")).toBeInTheDocument();
  });

  it("test_readingtime_with_one_minute_shows_one_min_text", () => {
    render(<ReadingTime minutes={1} />);

    expect(screen.getByText("1 min de leitura")).toBeInTheDocument();
  });

  it("test_readingtime_with_large_value_shows_correct_number", () => {
    render(<ReadingTime minutes={42} />);

    expect(screen.getByText("42 min de leitura")).toBeInTheDocument();
  });

  it("test_readingtime_undefined_returns_nothing", () => {
    const { container } = render(<ReadingTime minutes={undefined} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_readingtime_zero_returns_nothing", () => {
    // 0 is falsy — component must treat it the same as undefined.
    const { container } = render(<ReadingTime minutes={0} />);

    expect(container.innerHTML).toBe("");
  });

  it("test_readingtime_negative_returns_nothing", () => {
    const { container } = render(<ReadingTime minutes={-1} />);

    expect(container.innerHTML).toBe("");
  });
});

// ---------------------------------------------------------------------------
// CalloutBox — edge cases
// ---------------------------------------------------------------------------

describe("CalloutBox — edge cases", () => {
  it("test_calloutbox_unknown_type_falls_back_to_highlight_style", () => {
    // @ts-expect-error — intentionally testing invalid type
    const callout: Callout = { type: "unknown_type", content: "Test.", position: "intro" };

    const { container } = render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    const aside = container.querySelector("aside");
    // Falls back to highlight (agentColor as border)
    expect(aside).toHaveStyle({ borderColor: "#E8FF59" });
  });

  it("test_calloutbox_renders_as_aside_element", () => {
    const callout: Callout = { type: "note", content: "Semantic test.", position: "intro" };

    const { container } = render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(container.querySelector("aside")).toBeInTheDocument();
  });

  it("test_calloutbox_content_with_special_characters", () => {
    const callout: Callout = {
      type: "highlight",
      content: 'US$ 1.2B em "deals" — Q4/2025 & perspectivas',
      position: "intro",
    };

    render(<CalloutBox callout={callout} agentColor="#E8FF59" />);

    expect(screen.getByText('US$ 1.2B em "deals" — Q4/2025 & perspectivas')).toBeInTheDocument();
  });
});
