# Portaris — Home Assistant

Integração oficial do **[Portaris](https://portaris.app)** (controle de acesso DevPlus) para o
Home Assistant. Traz suas portas e leitores para o HA: estado em tempo (quase) real, abertura remota
e eventos de acesso para automações.

> Requer Home Assistant **2024.4** ou superior.

---

## O que ela expõe

Cada **porta** vira um dispositivo, cada **leitor** (DP Core Board) vira outro:

| Entidade | Plataforma | Descrição |
|----------|-----------|-----------|
| **Contato da porta** | `binary_sensor` (device class `door`) | Aberta/fechada — só em portas monitoradas |
| **Conectividade** | `binary_sensor` (device class `connectivity`) | Leitor Online/Offline |
| **Último heartbeat** | `sensor` (timestamp) | Última vez que o leitor reportou (desabilitado por padrão) |
| **Abrir** | `button` | Abre a porta — **só** em portas habilitadas na recepção e com o escopo `door:unlock` |
| **Acesso** | `event` | Dispara a cada evento (`Granted`, `Denied`, `DoorOpened`, `ManualUnlock`, …) |

O botão **Abrir** só aparece se o token tiver o escopo de abertura **e** a porta estiver marcada como
_"Habilitar na recepção"_ no painel — a mesma trava de segurança da tela de recepção do Portaris.

---

## Instalação (HACS)

1. HACS → **Integrações** → menu ⋮ → **Repositórios personalizados**.
2. Adicione `https://github.com/clayton-devplus/portaris-home-assistant` na categoria **Integration**.
3. Instale **Portaris** e reinicie o Home Assistant.

Instalação manual: copie `custom_components/portaris/` para o `config/custom_components/` do seu HA e reinicie.

---

## Configuração

1. No painel do Portaris: **Configurações → Integrações → Gerar token**.
   - Dê um nome (ex.: _Home Assistant_).
   - Marque as permissões: **Ler estado** (obrigatória) e, se quiser abrir portas pelo HA, **Abrir porta**.
   - **Copie o token na hora** — ele começa com `prtk_` e não é mostrado de novo.
2. No Home Assistant: **Configurações → Dispositivos e serviços → Adicionar integração → Portaris**.
   - **Endereço**: `https://app.portaris.app` (padrão).
   - **Token**: cole o `prtk_…`.

Se o token for revogado/expirar, o HA pede a renovação automaticamente (fluxo de reautenticação).

---

## Exemplo de automação

Notificar quando um acesso for **negado** na porta do escritório:

```yaml
automation:
  - alias: "Portaris — acesso negado no escritório"
    trigger:
      - platform: state
        entity_id: event.escritorio_acesso
    condition: "{{ trigger.to_state.attributes.event_type == 'Denied' }}"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Acesso negado na porta do escritório
            ({{ trigger.to_state.attributes.reason }}).
```

Abrir a porta por um botão do dashboard:

```yaml
service: button.press
target:
  entity_id: button.escritorio_abrir
```

---

## Como funciona (resumo técnico)

- Autenticação por **token de integração** (`Authorization: Bearer prtk_…`), independente do login do painel.
- O componente faz **polling** de `GET /doors`, `/readers` e `/events` a cada 30 s (`cloud_polling`).
- Os eventos são incrementais: o cursor é ancorado no `serverTime` do handshake, então o histórico
  **não** é reproduzido ao iniciar — só disparam acessos novos.
- A abertura chama `POST /doors/{id}/unlock`, que revalida no servidor (porta habilitada + leitor online).

Contrato completo da API: [`docs/integration-api.md`](https://github.com/clayton-devplus/portaris-api/blob/main/docs/integration-api.md) no repositório da API.

---

## Licença

[MIT](LICENSE) © DevPlus
