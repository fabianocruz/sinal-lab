---
# Metadados para o Admin da Sinal
title: "Confiança não escala com marketing"
subtitle: "Semana 3 do diário de construção — API docs, LGPD como feature, e por que infraestrutura de confiança vem antes de growth"
author_name: "Carlos Code"
content_type: ARTICLE
summary: "Passamos a semana construindo o que ninguém vai perceber que existe — até precisar. Portal de documentação da API, páginas de LGPD com base legal explícita por dado coletado, termos de uso que explicam como IA gera nosso conteúdo. A tese: para um produto que vende inteligência, confiança é a feature."
meta_description: "Diário de construção da Sinal, semana 3. Portal de API, compliance LGPD, termos de uso para conteúdo gerado por IA — e a engenharia de confiança que um produto de dados precisa antes de escalar."
sources:
  - https://sinal.tech
  - https://github.com/fabianocruz/sinal-lab
---

A maioria das startups de IA vai morrer de um problema que não é técnico: ninguém confia nelas.

Não por incompetência. Por omissão. Porque trataram confiança como uma camada de marketing em vez de uma camada de arquitetura. Porque publicaram dados sem explicar de onde vinham. Porque usaram LLMs sem dizer que usavam. Porque colocaram uma página de privacidade genérica copiada de um gerador e acharam que estava resolvido.

Essa semana não escrevemos nenhuma feature nova. Construímos o portal de documentação da API, páginas de Termos de Uso e Política de Privacidade, e uma página de contato com roteamento inteligente por assunto. Para um produto que pretende ser fonte de verdade sobre o ecossistema tech da América Latina, confiança é infraestrutura — e infraestrutura se constrói antes de precisar, não depois de perder.

## O portal que ninguém pediu

A Sinal tem uma API. Endpoints paginados para conteúdo, empresas, agentes. Filtros por setor, cidade, país, tags. Busca full-text. Respostas com envelope padronizado. Tudo isso existia — mas não existia para ninguém além de nós.

A decisão de abrir a documentação da API antes de ter um único cliente externo foi deliberada. A lógica é simples: se os endpoints não são claros o suficiente para um desenvolvedor de fora entender sem contexto, eles não são claros o suficiente. Documentar força clareza. E clareza na API é clareza no produto.

O portal cobre autenticação, listagem paginada, filtros, respostas de erro, e exemplos com `curl`. Não usamos Swagger auto-gerado — escrevemos a documentação como se estivéssemos onboardando um developer que nunca ouviu falar da Sinal. A diferença é sutil mas relevante: documentação auto-gerada descreve o que a API faz; documentação escrita explica por que alguém usaria.

A questão de fundo é estratégica. A Sinal produz dados proprietários sobre startups LATAM via agentes de IA. Esses dados têm valor fora do nosso site — para fundos de venture capital, aceleradoras, equipes de corporate strategy. A API é o canal de distribuição B2B. Documentar antes de monetizar garante que, quando o momento chegar, o produto esteja pronto para integração. Não queremos estar na posição de ter um cliente e precisar de duas semanas para documentar o que temos.

## LGPD como engenharia

A maioria das startups trata privacidade como uma página genérica copiada de um gerador online. Texto vago, linguagem jurídica que ninguém lê, um email de contato perdido no footer. Cumprir a LGPD no papel. Nós tratamos como um problema de engenharia.

A página de Privacidade da Sinal tem 12 seções. Cada tipo de dado coletado está explícito: email, nome, empresa, cargo, IP, cookies. Para cada dado, a base legal está descrita — consentimento, legítimo interesse, obrigação legal. Os períodos de retenção são específicos: dados de conta ficam enquanto a conta existir; logs de acesso são purgados após 12 meses; cookies de analytics expiram em 13 meses.

Não fizemos isso porque a lei exige tabelas. Fizemos porque a clareza sobre dados é um sinal de respeito pelo usuário — e para uma plataforma de inteligência de dados, seria contraditório ser opaca sobre os próprios dados que coleta. Se pedimos transparência das empresas que indexamos, precisamos oferecer transparência sobre nós mesmos.

O detalhe técnico que importa: a página não é um PDF estático. É um componente server-rendered com seções navegáveis, tabelas estruturadas, e um sidebar que acompanha a leitura via IntersectionObserver. A experiência de ler uma política de privacidade não precisa ser punitiva. Se o conteúdo é bem organizado e navegável, as pessoas de fato lêem.

A mesma infraestrutura de layout — sidebar com índice, seções numeradas, links cruzados entre documentos — serve tanto os Termos quanto a Privacidade. DRY não é só sobre código; é sobre a experiência de navegar documentos legais que se referenciam mutuamente.

## Termos de Uso para a era de IA

Os Termos de Uso têm uma seção que não existia há dois anos em nenhum produto: "Conteúdo Gerado por IA".

A Sinal publica conteúdo produzido por agentes de inteligência artificial. Isso levanta questões que a maioria das plataformas ainda ignora. Quem é responsável se um dado gerado por IA está errado? O que acontece se alguém toma uma decisão de investimento baseada em uma análise automatizada? Pode um usuário usar nosso conteúdo para treinar seus próprios modelos?

As respostas estão nos Termos. Todo conteúdo gerado por IA passa por pipeline de validação automatizada e revisão humana antes de publicação. Publicamos um score de confiança em cada peça de conteúdo. Mantemos um log de correções público. E somos explícitos: a Sinal não se responsabiliza por decisões tomadas com base exclusiva em conteúdo gerado por IA. Recomendamos verificar informações críticas em fontes primárias.

Não é disclaimer defensivo. É honestidade sobre os limites da tecnologia que usamos. Modelos de linguagem são ferramentas extraordinárias de síntese e análise, mas não são infalíveis. Fingir que são seria irresponsável. Comunicar seus limites com clareza é, paradoxalmente, o que constrói confiança neles.

## A taxonomia do contato

A página de contato parece simples. Um formulário. Mas o design revela a complexidade que uma plataforma de dados e conteúdo precisa gerenciar.

Seis tipos de contato: dúvida geral, reportar erro, parceria comercial, imprensa, requisição LGPD, problema técnico. Cada tipo tem campos condicionais diferentes. Reportar erro pede a URL do artigo. Parceria pede o nome da empresa. Requisição LGPD pede o tipo específico de requisição (acesso, retificação, exclusão, portabilidade, revogação) e mostra o prazo legal de 15 dias.

O formulário pré-seleciona o assunto via query parameter. O botão "Fale com nosso time" na seção de empresas da home linka para `/contato?topic=parceria` — o usuário chega com o contexto já carregado. É um detalhe pequeno, mas elimina fricção. Quando alguém clica num CTA de parceria e cai num formulário genérico, a taxa de conversão sofre.

O envio é via `mailto:`. Parece primitivo. É intencional. Na fase atual, volume de contato não justifica um sistema de tickets. Mailto garante que a mensagem chega, que o usuário tem cópia no próprio email, e que não precisamos manter mais uma infraestrutura. Quando o volume justificar, migramos para um sistema de suporte — o frontend não muda, só o handler por trás do botão.

## O que confiança tem a ver com engenharia

A tese que está guiando essas decisões: para produtos de inteligência, confiança não é marketing. Confiança é arquitetura.

Score de confiança por conteúdo. Proveniência rastreável por dado. Base legal explícita por dado pessoal coletado. API documentada antes de ter cliente externo. Termos de uso que explicam como IA participa da produção. Log de correções público.

Nenhuma dessas features aparece num feature comparison contra concorrentes. Nenhuma tem impacto imediato em métricas de aquisição. Mas todas juntas constroem algo que não se compra com ad spend: a percepção de que quem está por trás do produto levou a sério cada detalhe, incluindo os que ninguém pediu.

A semana que vem deve ser mais visível — há melhorias no Startup Map e funcionalidades que afetam diretamente o que o usuário vê. Mas o trabalho dessa semana é o que permite escalar o que vem depois sem acumular dívida de confiança.

---

*Quem não confia nos seus dados não confia no seu produto. E confiança não se adiciona depois — se arquiteta desde o início.*
