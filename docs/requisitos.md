# Checklist de requisitos da AV5

Cada requisito do enunciado está ligado ao lugar onde foi implementado e à forma como foi verificado.
Legenda: ✅ feito e verificado · ⚠️ feito com ressalva · ⬜ pendente.

Os testes citados ficam em `backend/tests/` (**216 testes**, todos passando; 95% de cobertura).

## 2.2 Requisitos mínimos da proposta própria

| Requisito | Status | Como o PortoFlow atende | Verificação |
| --- | --- | --- | --- |
| JWT e pelo menos 2 perfis com permissões distintas | ✅ | 3 perfis: `admin`, `operador`, `externo` | `test_permissoes_api.py` (401/403 em 22 rotas) |
| Pelo menos 5 entidades, com 1:N e uma N:N ou mestre-detalhe | ✅ | 11 tabelas; `agendamento → agendamento_container → container` | [modelagem.md](modelagem.md) |
| CRUD completo de pelo menos 2 entidades | ✅ | Containers e escalas (também usuários, clientes, navios e janelas), na API e na tela | `test_containers_api.py`, `test_cadastros_api.py` |
| Listagem com busca, filtro e paginação | ✅ | `GET /containers?busca=&status=&escala=&cliente=&pagina=` | `test_listagem_paginada`, `test_busca_por_parte_do_codigo_e_filtros` |
| Operação transacional em várias tabelas com regra de consistência | ✅ | Agendamento (baixa de vaga com `FOR UPDATE`) e gate-in | `test_janela_lotada_devolve_409_e_nao_grava_nada`, `test_gate_in_fora_da_janela_nao_grava_nada` |
| Usuário comum acessa só os próprios dados | ✅ | O externo só vê containers e agendamentos do seu cliente | `test_externo_so_ve_containers_do_proprio_cliente`, `test_meus_agendamentos_so_do_proprio_cliente` |

## 3.1 Requisitos funcionais (equivalentes)

| Código | Requisito da loja | Equivalente no PortoFlow | Status | Verificação |
| --- | --- | --- | --- | --- |
| RF01 | Cadastro e login: bcrypt, JWT, e-mail único | `/auth/registro` (externo pendente) e `/auth/login` | ✅ | `test_auth_api.py`, `test_seguranca.py` |
| RF02 | 401 sem token, 403 para cliente | `requer_papel` em `core/deps.py` | ✅ | `test_permissoes_api.py` |
| RF03 | CRUD de categorias, nome único | CRUD de escalas; (navio, viagem) único | ✅ | `test_crud_de_escala`, `test_escala_duplicada_devolve_409` |
| RF04 | CRUD de produtos, preço > 0 e estoque ≥ 0 na API | CRUD de containers; ISO 6346, peso > 0, tamanho 20/40 | ✅ | `test_peso_negativo_e_validado_na_api`, `test_codigo_com_digito_errado_devolve_422` |
| RF05 | Catálogo só de ativos, paginado, com busca e filtro | Lista de containers ativos | ✅ | `test_lista_vazia`, `test_desativar_e_soft_delete` |
| RF06 | Detalhe com "adicionar ao carrinho"; indica esgotado | Detalhe com histórico; indica **bloqueado**; caixa "agendar" na lista | ✅ | `test_detalhe_traz_escala_bloqueios_e_historico` |
| RF07 | Carrinho: quantidade ≤ estoque | Seleção (`SelecaoContext`): até 2 de 20' ou 1 de 40'; só janelas com vaga | ✅ | `test_caminhao_nao_leva_dois_containers_de_40`, `test_ultima_vaga_so_pode_ser_usada_uma_vez` |
| RF08 | Fechar pedido em uma transação, guardando o preço praticado | Agendar em uma transação; o histórico guarda origem e destino do momento | ✅ | `test_agendar_baixa_uma_vaga_e_vincula_containers`, `test_movimentar_grava_historico_com_origem_e_destino` |
| RF09 | Meus pedidos | Meus agendamentos (só do próprio cliente) | ✅ | `test_meus_agendamentos_so_do_proprio_cliente` |
| RF10 | Gestão de pedidos: listar e alterar status | Listar todos os agendamentos; cancelar; *cumprido* via portão | ✅ | `test_admin_lista_agendamentos_com_filtro`, `test_status_manual_so_aceita_cancelado` |

## 4. Requisitos não funcionais e stack

| Requisito | Status | Evidência |
| --- | --- | --- |
| PostgreSQL + Alembic | ✅ | `postgres:16-alpine`; `alembic/versions/0001_schema_inicial.py` |
| Python + FastAPI + Pydantic + SQLAlchemy | ✅ | `backend/requirements.txt` |
| React (Vite) consumindo a API via fetch/Axios | ✅ | `frontend/` (Axios em `src/api.js`) |
| Docker Compose com banco, API e front | ✅ | `docker-compose.yml` (projeto `portoflow`) |
| Git + GitHub, um repositório por grupo | ⬜ | **A pasta ainda não é um repositório Git.** Falta criar o repositório no GitHub e enviar. |
| Sobe do zero com `docker compose up` e seed com ≥ 1 admin, 3 categorias e 15 produtos | ✅ | Testado com `down -v` + `up --build`: 1 admin, 3 escalas, 20 containers. `test_seed.py` |
| Sem senha, chave JWT ou credencial no código; `.env.example`; consultas parametrizadas | ✅ | Tudo via `.env`. O CI gera segredos descartáveis a cada execução. Só ORM, sem SQL concatenado. |
| Responsivo (360 px e desktop) | ✅ | AppShell com menu recolhível; tabelas com rolagem própria. Capturas em 360 px. |
| Acessibilidade básica | ✅ | Mantine (`header`, `nav`, `main`, `label` em todos os campos, foco visível, teclado), `aria-label` nos botões de ícone, sem `<img>` sem `alt` |
| Carregando, erro e lista vazia em todas as telas que consomem a API | ✅ | Componente `Estado`, usado em todas as páginas com `useQuery` (checado por script) |
| Swagger em `/docs` com exemplos | ✅ | `test_swagger_disponivel` confere um exemplo |

## 5. Modelagem

| Requisito | Status | Evidência |
| --- | --- | --- |
| DER (conceitual) e modelo lógico | ✅ | [modelagem.md](modelagem.md) |
| Banco criado só por migrations | ✅ | Em produção o `create_all` não é usado; o CI roda `alembic check` (modelo = migration) |
| NUMERIC(10,2), nunca FLOAT (saber explicar) | ✅ | `peso_kg NUMERIC(10,2)`; explicação em [modelagem.md](modelagem.md) |
| Preço do momento da compra | ✅ | Histórico imutável de movimentações |
| NOT NULL, UNIQUE, CHECK e FK com ação de exclusão | ✅ | `test_restricoes_banco.py` (12 testes direto no banco) |
| Soft delete | ✅ | `ativo` / `status=inativo` |
| Índices de busca e filtro | ✅ | 13 índices; ver [modelagem.md](modelagem.md) |
| Carrinho no front ou no banco, com justificativa | ✅ | No front (`SelecaoContext`); justificativa em [modelagem.md](modelagem.md) |
| Transação única; sem estoque → nada gravado e 409 | ✅ | Agendamento e gate-in; testes de rollback |

## 6.1 Back-end

| Requisito | Status | Evidência |
| --- | --- | --- |
| REST: recursos no plural, verbos e códigos corretos | ✅ | [api.md](api.md); usa 200, 201, 204, 400, 401, 403, 404, 409 e 422 |
| Rotas mínimas (equivalentes) | ✅ | 26 rotas; tabela em [api.md](api.md) |
| Camadas: routers, schemas, services, repositories/models | ✅ | `backend/app/` |
| Regras de negócio nos serviços | ✅ | `services/` (os routers só delegam) |
| Valores calculados no servidor | ✅ | Status, posição, vagas e número do agendamento são sempre do servidor |
| Erros centralizados em JSON padronizado | ✅ | `core/errors.py`; formato em [api.md](api.md) |
| CORS só para a origem do front | ✅ | `test_cors_so_libera_a_origem_do_front` + teste real com curl |

## 6.2 Front-end

| Requisito | Status | Onde |
| --- | --- | --- |
| Catálogo com busca, filtro e paginação | ✅ | `pages/Containers.jsx` |
| Detalhe | ✅ | `components/DetalheContainer.jsx` |
| Carrinho | ✅ | `pages/Agendar.jsx` + `contexts/SelecaoContext.jsx` |
| Cadastro e login | ✅ | `pages/Entrada.jsx` |
| Meus pedidos | ✅ | `pages/Agendamentos.jsx` (cliente) |
| Área administrativa: produtos, categorias e pedidos | ✅ | Containers (criar, editar, desativar, bloquear), Cadastros (escalas, janelas, usuários, clientes), Agendamentos |
| Componentes reutilizáveis + React Router | ✅ | `components/`; `App.jsx` |
| Estado do carrinho e do usuário compartilhado (Context) | ✅ | `AuthContext`, `SelecaoContext` |
| Rotas admin protegidas no front **e** no back | ✅ | `RotaProtegida` + `requer_papel` |
| Validação no cliente + erros da API exibidos | ✅ | `util/validacao.js` (ISO 6346, placa, CNPJ); `errosPorCampo` / `mensagemErro` |
| Identidade visual coerente com o nicho | ✅ | Tema portuário (índigo), ícones de container e portão, códigos em fonte monoespaçada |

## 3.2 Opcionais (pontuação extra)

| Opcional | Status |
| --- | --- |
| Testes automatizados (pytest) em CI (GitHub Actions) | ⚠️ Pipeline pronto em `.github/workflows/testes.yml`; só roda depois do envio ao GitHub |
| Painel administrativo com indicadores | ⚠️ Parcial: a tela Pátio mostra a ocupação (%). Sem painel dedicado. |
| Upload de imagem | ⬜ Não se aplica diretamente (seria foto de avaria ou lacre) |
| Cupom / avaliação | — Não se aplicam ao tema |
| Deploy público | ⬜ |

## Diferenças em relação ao documento de casos de uso

| Caso de uso | Diferença | Motivo |
| --- | --- | --- |
| UC04 (2a): "registra a ocorrência" quando o caminhão é barrado | A recusa é exibida e explicada, mas não é gravada | Sugerido como próximo passo ([ux-insights.md](ux-insights.md)) |
| UC07: "a consulta é registrada em log" | Sem log de consultas | Fora do mínimo do enunciado |
| UC08: "envia o acesso inicial" | O admin define a senha inicial | Envio de e-mail fora da stack (ajuste 5.2 do planejamento) |
