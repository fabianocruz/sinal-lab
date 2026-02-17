"""Example usage of the editorial validation module.

This demonstrates how AI agents can use the editorial module to validate
their outputs before publication.
"""

from packages.editorial import validate_content, classify_territory


# Example 1: High-quality fintech content (should pass)
def example_good_fintech_content():
    """Example of content that passes editorial bar."""
    title = "Pix alcança 3 bilhões de transações mensais — análise do crescimento"
    content = """
    O Pix atingiu 3 bilhões de transações mensais em janeiro de 2026,
    representando um crescimento de 45% em relação ao mesmo período de 2025,
    segundo dados do Banco Central do Brasil.

    A decomposição por tipo de transação revela que:
    - P2P (pessoa-física para pessoa-física): 1.8 bilhões (60%)
    - P2B (pessoa-física para empresas): 900 milhões (30%)
    - B2B (empresas para empresas): 300 milhões (10%)

    O volume financeiro movimentado foi de R$ 850 bilhões no mês, com ticket
    médio de R$ 283 — queda de 8% vs 2025, indicando maior adoção em transações
    de menor valor.

    Oportunidades para desenvolvedores:
    - APIs de pagamento via Pix representam 15% do volume total
    - Tempo médio de integração: 2-3 semanas
    - Custo por transação: R$ 0,01 a R$ 0,15 dependendo do provedor

    Comparativo LATAM: México (CoDi) processa 200M transações/mês, Colômbia
    em fase piloto com 5M transações/mês.

    Fontes: Banco Central do Brasil (relatório jan/2026), análise própria
    de dados públicos do Open Finance.
    """

    metadata = {
        "sources": [
            "https://www.bcb.gov.br/estabilidadefinanceira/pix",
            "https://dados.gov.br/openfinance"
        ],
        "agent": "MERCADO",
        "confidence_dq": 0.85,
        "confidence_ac": 0.80,
    }

    result = validate_content(content, metadata=metadata, title=title)

    print("=" * 70)
    print("EXEMPLO 1: Conteúdo Fintech de Alta Qualidade")
    print("=" * 70)
    print(f"\nTítulo: {title}\n")
    print(result.summary())
    print(f"\nCritérios atendidos:")
    for criterion, passed in result.criteria_met.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}")

    if result.territory_classification:
        print(f"\nTerritório: {result.territory_classification.primary_territory}")
        print(f"Confiança: {result.territory_classification.confidence:.2f}")
        print(f"Secundários: {result.territory_classification.secondary_territories}")

    print(f"\n{'APROVADO PARA PUBLICAÇÃO' if result.passes_editorial_bar else 'REPROVADO'}")
    print()

    return result


# Example 2: Low-quality press release (should fail)
def example_bad_press_release():
    """Example of content that fails editorial bar."""
    title = "Startup anuncia nova rodada de investimento"
    content = """
    A XYZ Corp tem o prazer de anunciar que levantou uma rodada de investimento.

    A empresa vai usar os recursos para crescimento e expansão na América Latina.
    O CEO afirmou: "Estamos muito animados com essa oportunidade revolucionária
    que vai mudar o mercado."

    A XYZ Corp é uma fintech inovadora focada em inclusão financeira.
    """

    metadata = {
        "sources": ["https://xyz.com/press-release"],
        "agent": "FUNDING",
    }

    result = validate_content(content, metadata=metadata, title=title)

    print("=" * 70)
    print("EXEMPLO 2: Press Release Sem Análise (Low Quality)")
    print("=" * 70)
    print(f"\nTítulo: {title}\n")
    print(result.summary())
    print(f"\nCritérios atendidos:")
    for criterion, passed in result.criteria_met.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}")

    if result.red_flags:
        print(f"\n⚠️  Red Flags:")
        for flag in result.red_flags:
            print(f"  - {flag}")

    if result.recommendations:
        print(f"\n💡 Recomendações:")
        for rec in result.recommendations:
            print(f"  - {rec}")

    print(f"\n{'APROVADO PARA PUBLICAÇÃO' if result.passes_editorial_bar else 'REPROVADO'}")
    print()

    return result


# Example 3: Territory classification only
def example_territory_classification():
    """Example of using territory classification independently."""
    examples = [
        ("Nubank reporta 100M de clientes no Brasil", "fintech"),
        ("Como usar GPT-4 para detecção de fraude em pagamentos", "ai"),
        ("Drex: piloto do CBDC brasileiro entra em fase 2", "cripto"),
        ("Benchmark de custos AWS São Paulo vs Virgínia", "engenharia"),
        ("Sequoia investe R$ 50M em fintech brasileira", "venture"),
        ("AgTech usa IA para prever safra de soja no Mato Grosso", "green_agritech"),
    ]

    print("=" * 70)
    print("EXEMPLO 3: Classificação de Territórios")
    print("=" * 70)
    print()

    for title, expected in examples:
        result = classify_territory(content="", title=title)
        match = "✅" if result.primary_territory == expected else "❌"
        print(f"{match} '{title[:50]}...'")
        print(f"   → {result.primary_territory} (confiança: {result.confidence:.2f})")
        print()


if __name__ == "__main__":
    # Run all examples
    example_good_fintech_content()
    print("\n")
    example_bad_press_release()
    print("\n")
    example_territory_classification()
