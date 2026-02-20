import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock lucide-react icons before importing the component that uses them
vi.mock('lucide-react', () => ({
  Menu: () => <span data-testid="menu-icon" />,
  X: () => <span data-testid="x-icon" />,
}));

import Navbar from './Navbar';
import Footer from './Footer';
import Section from './Section';

// ---------------------------------------------------------------------------
// Navbar
// ---------------------------------------------------------------------------

describe('Navbar', () => {
  describe('brand', () => {
    it('test_navbar_brand_renders_sinal_text', () => {
      render(<Navbar />);
      // getAllByText because "Sinal" also appears in "Sinal.lab" copyright-like
      // text in Footer — but here we only render Navbar, so one match.
      expect(screen.getByText('Sinal')).toBeInTheDocument();
    });

    it('test_navbar_brand_link_points_to_root', () => {
      render(<Navbar />);
      // The brand "Sinal" text is inside the logo anchor
      const brandLink = screen.getByText('Sinal').closest('a');
      expect(brandLink).toHaveAttribute('href', '/');
    });

    it('test_navbar_signal_dot_is_rendered', () => {
      render(<Navbar />);
      // The signal dot is a <span> that is a sibling of the "Sinal" text
      // inside the logo anchor. It has no text content — we locate it via
      // the parent anchor.
      const brandLink = screen.getByText('Sinal').closest('a');
      expect(brandLink).not.toBeNull();
      // The dot span has bg-signal class
      const dot = brandLink!.querySelector('span.bg-signal');
      expect(dot).toBeInTheDocument();
    });
  });

  describe('desktop nav links', () => {
    it('test_navbar_renders_briefing_link', () => {
      render(<Navbar />);
      expect(screen.getByRole('link', { name: 'Briefing' })).toBeInTheDocument();
    });

    it('test_navbar_renders_metodologia_link', () => {
      render(<Navbar />);
      expect(screen.getByRole('link', { name: 'Metodologia' })).toBeInTheDocument();
    });

    it('test_navbar_renders_precos_link', () => {
      render(<Navbar />);
      expect(screen.getByRole('link', { name: 'Precos' })).toBeInTheDocument();
    });

    it('test_navbar_renders_para_empresas_link', () => {
      render(<Navbar />);
      expect(screen.getByRole('link', { name: 'Para Empresas' })).toBeInTheDocument();
    });

    it('test_navbar_renders_arquivo_link', () => {
      render(<Navbar />);
      // Multiple "Arquivo" links exist (desktop + mobile after toggle), but
      // before toggle only the desktop one is in the DOM.
      const arquivoLinks = screen.getAllByRole('link', { name: 'Arquivo' });
      expect(arquivoLinks.length).toBeGreaterThanOrEqual(1);
    });

    it('test_navbar_briefing_link_href_is_correct', () => {
      render(<Navbar />);
      expect(screen.getByRole('link', { name: 'Briefing' })).toHaveAttribute('href', '/#briefing');
    });
  });

  describe('CTA button', () => {
    it('test_navbar_cta_assine_o_briefing_is_rendered', () => {
      render(<Navbar />);
      // There is always at least one CTA (the desktop one)
      const ctaLinks = screen.getAllByRole('link', { name: 'Assine o Briefing' });
      expect(ctaLinks.length).toBeGreaterThanOrEqual(1);
    });

    it('test_navbar_cta_points_to_hero_section', () => {
      render(<Navbar />);
      const ctaLinks = screen.getAllByRole('link', { name: 'Assine o Briefing' });
      // All CTA links should point to /#hero
      ctaLinks.forEach((link) => {
        expect(link).toHaveAttribute('href', '/#hero');
      });
    });
  });

  describe('mobile menu toggle', () => {
    it('test_navbar_mobile_toggle_button_exists', () => {
      render(<Navbar />);
      const toggle = screen.getByRole('button', { name: 'Abrir menu' });
      expect(toggle).toBeInTheDocument();
    });

    it('test_navbar_mobile_toggle_shows_menu_icon_when_closed', () => {
      render(<Navbar />);
      expect(screen.getByTestId('menu-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('x-icon')).not.toBeInTheDocument();
    });

    it('test_navbar_mobile_toggle_opens_mobile_menu_on_click', () => {
      render(<Navbar />);
      const toggle = screen.getByRole('button', { name: 'Abrir menu' });

      // Mobile menu links are NOT in the DOM before toggling
      // Verify by counting "Briefing" links — only 1 (desktop) before toggle
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(1);

      fireEvent.click(toggle);

      // After toggle, both desktop and mobile links are rendered
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(2);
    });

    it('test_navbar_mobile_toggle_shows_x_icon_when_open', () => {
      render(<Navbar />);
      const toggle = screen.getByRole('button', { name: 'Abrir menu' });
      fireEvent.click(toggle);

      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('menu-icon')).not.toBeInTheDocument();
    });

    it('test_navbar_mobile_toggle_aria_label_changes_when_open', () => {
      render(<Navbar />);
      const toggle = screen.getByRole('button', { name: 'Abrir menu' });
      fireEvent.click(toggle);

      expect(screen.getByRole('button', { name: 'Fechar menu' })).toBeInTheDocument();
    });

    it('test_navbar_mobile_toggle_closes_menu_on_second_click', () => {
      render(<Navbar />);
      const toggle = screen.getByRole('button', { name: 'Abrir menu' });

      fireEvent.click(toggle);
      // Menu is open — Briefing appears twice
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(2);

      fireEvent.click(screen.getByRole('button', { name: 'Fechar menu' }));
      // Menu is closed — Briefing appears once again
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(1);
    });

    it('test_navbar_mobile_menu_shows_all_nav_links', () => {
      render(<Navbar />);
      fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }));

      // Every nav link should now have two instances (desktop + mobile)
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(2);
      expect(screen.getAllByRole('link', { name: 'Metodologia' })).toHaveLength(2);
      expect(screen.getAllByRole('link', { name: 'Precos' })).toHaveLength(2);
      expect(screen.getAllByRole('link', { name: 'Para Empresas' })).toHaveLength(2);
      expect(screen.getAllByRole('link', { name: 'Arquivo' })).toHaveLength(2);
    });

    it('test_navbar_mobile_menu_shows_cta_button', () => {
      render(<Navbar />);
      fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }));

      const ctaLinks = screen.getAllByRole('link', { name: 'Assine o Briefing' });
      // Desktop (hidden via CSS) + mobile = 2
      expect(ctaLinks).toHaveLength(2);
    });

    it('test_navbar_clicking_mobile_link_closes_menu', () => {
      render(<Navbar />);
      fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }));

      // Both desktop and mobile "Briefing" links are rendered — click the
      // second one (the mobile instance)
      const briefingLinks = screen.getAllByRole('link', { name: 'Briefing' });
      fireEvent.click(briefingLinks[1]);

      // Mobile menu should close — back to 1 "Briefing" link
      expect(screen.getAllByRole('link', { name: 'Briefing' })).toHaveLength(1);
    });
  });

  describe('scroll behaviour', () => {
    it('test_navbar_starts_without_scrolled_styles', () => {
      render(<Navbar />);
      const nav = screen.getByRole('navigation');
      expect(nav.className).toContain('bg-transparent');
    });

    it('test_navbar_adds_backdrop_class_on_scroll', () => {
      render(<Navbar />);

      // Simulate scroll past the 40px threshold
      Object.defineProperty(window, 'scrollY', { writable: true, value: 50 });
      fireEvent.scroll(window);

      const nav = screen.getByRole('navigation');
      expect(nav.className).toContain('backdrop-blur-xl');
    });

    it('test_navbar_removes_backdrop_class_when_scroll_returns_to_top', () => {
      render(<Navbar />);

      // Scroll down
      Object.defineProperty(window, 'scrollY', { writable: true, value: 50 });
      fireEvent.scroll(window);

      // Scroll back up
      Object.defineProperty(window, 'scrollY', { writable: true, value: 0 });
      fireEvent.scroll(window);

      const nav = screen.getByRole('navigation');
      expect(nav.className).toContain('bg-transparent');
    });
  });
});

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

describe('Footer', () => {
  describe('brand', () => {
    it('test_footer_renders_sinal_brand_text', () => {
      render(<Footer />);
      expect(screen.getByText('Sinal')).toBeInTheDocument();
    });

    it('test_footer_brand_link_points_to_root', () => {
      render(<Footer />);
      const brandLink = screen.getByText('Sinal').closest('a');
      expect(brandLink).toHaveAttribute('href', '/');
    });

    it('test_footer_renders_signal_dot', () => {
      render(<Footer />);
      const brandLink = screen.getByText('Sinal').closest('a');
      const dot = brandLink!.querySelector('span.bg-signal');
      expect(dot).toBeInTheDocument();
    });

    it('test_footer_renders_tagline', () => {
      render(<Footer />);
      expect(screen.getByText('Inteligencia aberta para quem constroi.')).toBeInTheDocument();
    });
  });

  describe('column headings', () => {
    it('test_footer_renders_produto_column_heading', () => {
      render(<Footer />);
      expect(screen.getByText('Produto')).toBeInTheDocument();
    });

    it('test_footer_renders_comunidade_column_heading', () => {
      render(<Footer />);
      expect(screen.getByText('Comunidade')).toBeInTheDocument();
    });

    it('test_footer_renders_transparencia_column_heading', () => {
      render(<Footer />);
      expect(screen.getByText('Transparencia')).toBeInTheDocument();
    });

    it('test_footer_renders_institucional_column_heading', () => {
      render(<Footer />);
      expect(screen.getByText('Institucional')).toBeInTheDocument();
    });
  });

  describe('footer links', () => {
    it('test_footer_renders_briefing_semanal_link', () => {
      render(<Footer />);
      expect(screen.getByRole('link', { name: 'Briefing Semanal' })).toBeInTheDocument();
    });

    it('test_footer_briefing_semanal_points_to_newsletter', () => {
      render(<Footer />);
      expect(screen.getByRole('link', { name: 'Briefing Semanal' })).toHaveAttribute('href', '/newsletter');
    });

    it('test_footer_renders_metodologia_link', () => {
      render(<Footer />);
      expect(screen.getByRole('link', { name: 'Metodologia' })).toBeInTheDocument();
    });

    it('test_footer_renders_sobre_link', () => {
      render(<Footer />);
      expect(screen.getByRole('link', { name: 'Sobre' })).toBeInTheDocument();
    });

    it('test_footer_renders_para_empresas_link', () => {
      render(<Footer />);
      expect(screen.getByRole('link', { name: 'Para Empresas' })).toBeInTheDocument();
    });
  });

  describe('social links', () => {
    it('test_footer_renders_linkedin_social_link', () => {
      render(<Footer />);
      const link = screen.getByRole('link', { name: 'LinkedIn' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://linkedin.com/company/sinal-lab');
    });

    it('test_footer_renders_x_social_link', () => {
      render(<Footer />);
      const link = screen.getByRole('link', { name: 'X' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://x.com/sinal_lab');
    });

    it('test_footer_renders_github_social_link', () => {
      render(<Footer />);
      const link = screen.getByRole('link', { name: 'GitHub' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://github.com/fabianocruz/sinal-lab');
    });

    it('test_footer_social_links_open_in_new_tab', () => {
      render(<Footer />);
      ['LinkedIn', 'X', 'GitHub'].forEach((name) => {
        const link = screen.getByRole('link', { name });
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      });
    });
  });

  describe('bottom bar', () => {
    it('test_footer_renders_transparency_tagline', () => {
      render(<Footer />);
      expect(
        screen.getByText('Transparencia radical. Metodologia aberta. Dados verificaveis.'),
      ).toBeInTheDocument();
    });

    it('test_footer_renders_copyright_with_current_year', () => {
      render(<Footer />);
      const year = new Date().getFullYear().toString();
      // The copyright text contains the year and "Sinal.lab"
      const copyright = screen.getByText((content) =>
        content.includes(year) && content.includes('Sinal.lab'),
      );
      expect(copyright).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Section
// ---------------------------------------------------------------------------

describe('Section', () => {
  describe('children', () => {
    it('test_section_renders_children_content', () => {
      render(
        <Section>
          <p>Hello world</p>
        </Section>,
      );
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });

    it('test_section_renders_multiple_children', () => {
      render(
        <Section>
          <span>First</span>
          <span>Second</span>
        </Section>,
      );
      expect(screen.getByText('First')).toBeInTheDocument();
      expect(screen.getByText('Second')).toBeInTheDocument();
    });
  });

  describe('label prop', () => {
    it('test_section_renders_label_text_when_provided', () => {
      render(<Section label="Destaques">Content</Section>);
      expect(screen.getByText('Destaques')).toBeInTheDocument();
    });

    it('test_section_renders_signal_line_when_label_is_provided', () => {
      const { container } = render(<Section label="Destaques">Content</Section>);
      // The signal line is a <span> with bg-signal class inside the label wrapper
      const line = container.querySelector('span.bg-signal');
      expect(line).toBeInTheDocument();
    });

    it('test_section_does_not_render_label_area_when_label_is_omitted', () => {
      const { container } = render(<Section>Content</Section>);
      // No span with bg-signal should exist when label is absent
      const line = container.querySelector('span.bg-signal');
      expect(line).not.toBeInTheDocument();
    });

    it('test_section_does_not_render_label_area_when_label_is_empty_string', () => {
      const { container } = render(<Section label="">Content</Section>);
      // An empty string is falsy so the label block should not render
      const line = container.querySelector('span.bg-signal');
      expect(line).not.toBeInTheDocument();
    });
  });

  describe('className prop', () => {
    it('test_section_applies_custom_classname', () => {
      const { container } = render(<Section className="custom-class">Content</Section>);
      const section = container.querySelector('section');
      expect(section).toHaveClass('custom-class');
    });

    it('test_section_keeps_base_classes_when_custom_classname_is_added', () => {
      const { container } = render(<Section className="custom-class">Content</Section>);
      const section = container.querySelector('section');
      // Base classes from cn() must still be present
      expect(section).toHaveClass('border-b');
    });

    it('test_section_works_without_classname_prop', () => {
      const { container } = render(<Section>Content</Section>);
      const section = container.querySelector('section');
      expect(section).toBeInTheDocument();
    });
  });

  describe('id prop', () => {
    it('test_section_applies_id_when_provided', () => {
      const { container } = render(<Section id="briefing">Content</Section>);
      const section = container.querySelector('section');
      expect(section).toHaveAttribute('id', 'briefing');
    });

    it('test_section_has_no_id_attribute_when_not_provided', () => {
      const { container } = render(<Section>Content</Section>);
      const section = container.querySelector('section');
      expect(section).not.toHaveAttribute('id');
    });
  });

  describe('combined props', () => {
    it('test_section_renders_correctly_with_all_props', () => {
      const { container } = render(
        <Section id="hero" label="Hero Section" className="extra-class">
          <h1>Title</h1>
        </Section>,
      );
      const section = container.querySelector('section');
      expect(section).toHaveAttribute('id', 'hero');
      expect(section).toHaveClass('extra-class');
      expect(screen.getByText('Hero Section')).toBeInTheDocument();
      expect(screen.getByText('Title')).toBeInTheDocument();
    });
  });
});
