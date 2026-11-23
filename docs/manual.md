# Manual de uso

Acesse **http://localhost:5173**. Cada perfil vê um menu diferente e começa numa tela diferente.

| Perfil | Tela inicial | Menu |
| --- | --- | --- |
| Operador | Portão | Portão · Pátio · Containers · Agendamentos · Meu perfil |
| Administrador | Containers | Containers · Portão · Pátio · Agendamentos · Cadastros · Meu perfil |
| Cliente (externo) | Meus containers | Meus containers · Agendar · Meus agendamentos · Meu perfil |

## Operador

### Receber ou liberar um caminhão (Portão)

1. Com o cursor já no campo, digite a **placa** do caminhão e tecle **Enter**. Também servem o código do container
   ou o número do agendamento (`AG...`).
2. Aparece um cartão por container do caminhão, com a operação esperada (**ENTRADA** ou **SAÍDA**).
   - **Verde, com botão "Registrar":** está tudo certo. Na entrada, a tela mostra em destaque a posição do pátio
     para onde o container deve ir.
   - **Vermelho, com "Não liberar o caminhão":** a tela lista cada problema e o que fazer. Por exemplo: sem
     agendamento, fora da janela, container bloqueado, ou outro container em cima.
3. Confira a placa do caminhão. Se for diferente da agendada, a tela pede uma justificativa, que fica gravada
   no histórico.
4. Tecle **Enter** de novo (o botão já está com foco) para registrar. Quando o caminhão termina, o campo limpa
   e o foco volta para o próximo.

O quadro **Registrados neste turno** mostra as últimas operações, para conferência.

### Mover um container (Pátio)

1. O mapa mostra cada bloco por fileira e pilha. O número na célula é quantos containers estão empilhados;
   uma borda vermelha indica container bloqueado na pilha.
2. Para achar um container, digite o código em **Localizar container** e tecle Enter.
3. Clique na pilha. Só o container do **topo** pode ser movido.
4. Em **Mover**, escolha a nova posição. A lista mostra só as posições livres e com apoio embaixo.

### Consultar e cadastrar containers

Em **Containers**:
- Busque por parte do código e filtre por status; clique numa linha para ver o detalhe e o histórico.
- No detalhe, **Editar** altera tamanho, tipo, peso e escala. **Desativar** faz soft delete, e não é permitido
  para container no pátio.
- **Novo container** cadastra um container. O código passa pela validação ISO 6346, com dígito verificador,
  já no formulário.

## Cliente (transportadora ou despachante)

1. **Solicitar acesso:** na tela de login, informe nome, e-mail, senha e o CNPJ da empresa. A empresa já precisa
   ser cliente do terminal. O acesso libera quando o administrador aprovar.
2. **Escolher containers:** em **Meus containers**, marque até 2 de 20' ou 1 de 40'. Containers que não podem
   ser escolhidos aparecem desabilitados, com o motivo ao passar o mouse (bloqueado, mistura de entrega com
   retirada etc.). A seleção vale entre as telas.
3. **Agendar:** em **Agendar**, confira os containers, escolha o dia e uma janela com vaga, e informe a placa e
   o motorista. O número `AG...` gerado (ou a placa) é o que o portão vai pedir.
4. **Acompanhar:** **Meus agendamentos** lista os agendamentos da sua empresa. Um agendamento confirmado
   pode ser cancelado, e a vaga volta para a janela.

## Administrador

Tudo o que o operador faz, e mais:
- **Bloquear ou liberar um container:** no detalhe do container, informe o motivo e bloqueie. Isso cancela as
  retiradas agendadas e devolve as vagas. **Liberar** encerra o bloqueio.
- **Cadastros:**
  - **Escalas:** cadastrar navios e escalas, editar, avançar o status (prevista → atracada → encerrada) e desativar.
  - **Janelas:** criar janelas por dia, com duração e vagas. Uma janela só pode ser removida enquanto não tiver
    agendamento.
  - **Usuários:** aprovar cadastros **pendentes**, criar operadores, administradores e clientes, e desativar usuários.
  - **Clientes:** cadastrar empresas por CNPJ, desativar e reativar.

## Usuários de teste

O seed cria os usuários abaixo. As senhas vêm do `.env` (`SEED_SENHA_ADMIN` e `SEED_SENHA_PADRAO`).

| Perfil | E-mail |
| --- | --- |
| Administrador | admin@portoflow.com.br |
| Operador | operador@portoflow.com.br |
| Cliente (Transportes Oeste) | ana@transportesoeste.com.br |
| Cliente (Importadora Sul) | bruno@importadorasul.com.br |
