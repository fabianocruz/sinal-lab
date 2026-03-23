---
# Metadados para o Admin da Sinal
title: "Ninguém sabe quantas startups existem na América Latina"
subtitle: "Semana 2 do diário de construção — como estamos montando um índice unificado a partir de dados regulatórios, 22 fontes e um engine de deduplicação"
author_name: "Santos de Machine"
content_type: ARTICLE
summary: "Passamos a semana construindo o INDEX, nosso sexto agente de IA — um registro unificado de startups LATAM a partir de fontes como Receita Federal, SEC, Banco Central e Crunchbase. O desafio real não é coletar. É deduplicar."
meta_description: "Diário de construção da Sinal, semana 2. Como estamos indexando startups LATAM cruzando Receita Federal, SEC, Banco Central e Crunchbase com um engine de entity resolution em cascata."
sources:
  - https://sinal.tech
  - https://github.com/fabianocruz/sinal-lab
---

Passamos a semana inteira tentando responder uma pergunta que parece simples: quantas startups de tecnologia existem na América Latina? A resposta honesta é que ninguém sabe. O Crunchbase tem um número. A ABStartups tem outro. O Y Combinator lista um punhado de portfólio com sede na região. O GitHub revela organizações ativas em São Paulo, Cidade do México, Bogotá. Mas nenhuma dessas fontes concorda com as outras. E pior: muitas vezes estão falando da mesma empresa com nomes diferentes.

Essa é a oportunidade que estamos perseguindo. Não porque contar startups seja o objetivo — mas porque quem resolve o problema de identificação resolve, de quebra, o problema de inteligência. E inteligência proprietária sobre o ecossistema LATAM é o moat que estamos construindo.

## Coletar tudo, filtrar depois

A Sinal já operava com cinco agentes de IA. Cada um cobre um ângulo: curadoria de notícias, tendências técnicas, ecossistema dev, rodadas de investimento, mapeamento de mercado. Essa semana lançamos o sexto: o INDEX.

O INDEX é diferente dos outros. Não produz texto. Produz um registro. Um índice unificado de startups construído a partir de seis fontes independentes — dados da Receita Federal (CNPJ), ABStartups, portfólio do Y Combinator, Crunchbase, e organizações no GitHub. A ambição é mapear o ecossistema inteiro, não apenas as empresas que aparecem na imprensa.

A decisão arquitetural mais importante que tomamos aqui: o INDEX não tem filtro editorial. Ele indexa tudo. A curadoria acontece em outra camada, quando os dados precisam virar publicação. Parece óbvio, mas a maioria das plataformas de inteligência de mercado mistura coleta com curadoria — e acaba perdendo cobertura porque descarta cedo demais o que não parece relevante hoje. Dados sobre uma startup desconhecida em Medellín podem parecer irrelevantes em fevereiro e virar a história principal em agosto.

## O problema que ninguém quer resolver

O desafio real do INDEX não é coletar. É deduplicar.

A mesma empresa aparece como "NU PAGAMENTOS S.A." na Receita Federal, "Nubank" no Crunchbase, "nubank" na ABStartups e "nu-bank" no GitHub. Quatro fontes, quatro grafias, uma empresa. Multiplique isso por milhares de startups e o problema escala rápido.

Construímos um engine de matching em cascata. Primeiro tenta bater o CNPJ — se bate, é a mesma empresa, ponto final. Depois tenta o domínio web normalizado. Depois o identificador do Crunchbase. Só em último caso usa matching fuzzy de nome combinado com cidade. Cada nível tem um score de confiança explícito: dado de governo é 1.0, domínio é 0.95, nome fuzzy é 0.72.

Por que isso importa? Porque a qualidade de qualquer produto de inteligência depende da qualidade da identificação de entidades. Se o sistema conta a mesma empresa duas vezes, os números de mercado estão errados. Se não consegue ligar uma rodada de investimento à empresa certa, a análise de funding é ruim. Entity resolution é a infraestrutura invisível que sustenta tudo que vem depois.

## Quando o governo vira sua melhor API

Uma coisa que aprendemos rápido: fontes regulatórias são subestimadas no ecossistema de dados de startups.

A SEC publica Form D filings — registros obrigatórios de captação privada nos EUA. Empresas LATAM com subsidiárias americanas aparecem ali. O Banco Central do Brasil mantém um registro público de todas as instituições financeiras autorizadas. A Receita Federal tem o CNPJ de toda empresa registrada no país, com CNAE (código de atividade econômica) que permite filtrar por 42 categorias de tecnologia.

São fontes que nenhuma startup reporta voluntariamente ao Crunchbase, mas que existem em registros públicos com autoridade legal. Integramos as três essa semana, junto com dados de vagas da Gupy que revelam stack tecnológico e tamanho de time.

O cross-reference engine cruza essas fontes. Se o FUNDING detecta uma rodada via Crunchbase, o sistema verifica se existe um Form D correspondente na SEC. Se existe, a confiança sobe. Se a empresa é fintech e aparece no registro do BCB, sobe mais. Se não aparece em nenhuma fonte regulatória, a confiança não cai — mas a ausência fica explícita. Transparência sobre o que sabemos e o que não sabemos é parte do produto.

## Dados sintéticos mentem

Com a infraestrutura pronta, rodamos os agentes de verdade pela primeira vez em escala. Não mais com dados inventados — mas coletando de RSS, APIs e datasets públicos, passando pelo pipeline editorial, e persistindo no banco.

O batch começou. E quebrou.

Papers do arXiv com 15 co-autores estouraram o limite do campo de autor. URLs do Google News — que codifica o destino em Base64 dentro de um redirect monstruoso — estouraram o limite do campo de URL. Dois campos que pareciam dimensionados com folga nos testes com dados sintéticos simplesmente não comportavam o mundo real.

É uma lição que se repete em todo projeto de dados: schemas desenhados contra dados inventados vão quebrar em produção. A única forma de validar limites é enfrentar dados reais. Corrigimos, adicionamos guards defensivos, e o batch voltou a rodar.

Mas não foram só os limites de schema. Fontes que funcionavam perfeitamente em testes isolados falharam no batch real: Google Trends retornou 404 para queries LATAM, Lobsters mudou de URL sem aviso, Bluesky cortou o rate limit da API pública. Nenhuma falha é fatal — o sistema loga e continua. Mas revelou que precisamos de health checks automáticos: quando uma fonte degrada silenciosamente, a qualidade do output degrada junto, e ninguém percebe até que o editorial reclame.

## Onde estamos

A Sinal hoje opera com 6 agentes, 22 fontes de dados (incluindo 4 regulatórias), quase 2.500 testes automatizados entre backend e frontend, e 8 endpoints de API. O batch de 30 edições está rodando enquanto escrevo — são cinco agentes gerando conteúdo real, passando pelo pipeline editorial, acumulando evidências no banco.

Quando terminar, vamos substituir todo o conteúdo sintético da produção pelo conteúdo gerado pelos agentes. É um marco. Significa que o site vai mostrar output real da plataforma, não mockups.

## O que vem agora

A próxima prioridade é o Startup Map — a primeira interface pública do INDEX. Páginas programáticas para cada startup indexada, com dados agregados de múltiplas fontes, score de confiança, e links para evidências. É onde a tese da Sinal começa a virar produto visível: inteligência proprietária servida via API e páginas otimizadas para busca.

Também precisamos resolver o monitoramento de fontes. Hoje, se o Google Trends para de responder, só descobrimos quando rodamos o batch. Precisamos de alertas proativos — uma fonte que falha por 48 horas seguidas deveria disparar um aviso antes que o output do agente sofra.

Sinal fraco da semana: a dificuldade de encontrar dados confiáveis sobre startups LATAM não é um problema de tecnologia. É um problema de fragmentação institucional. Cada país tem seus registros, suas associações, seus eventos. Não existe um "Crunchbase da América Latina" porque não existe uma América Latina unificada em termos de dados. Quem construir essa unificação não está fazendo um produto de mídia — está construindo infraestrutura.

---

*O moat não é o modelo de IA. É o índice que o modelo alimenta.*
