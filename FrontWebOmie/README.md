# Envio de faturamento

Front-end em Streamlit que permite o usuário enviar um arquivo de faturamento (xlsx/xlsb/csv) e seu email para o backend em N8N. O arquivo é codificado em Base64 e enviado via POST JSON.

---

## Como funciona

1. Usuário acessa o app no navegador.
2. Informa a URL do webhook N8N, seu email e seleciona o arquivo.
3. Ao clicar em **Enviar**, o app:
   - Valida email (regex) e os campos obrigatórios.
   - Converte o arquivo para Base64.
   - Envia um POST JSON ao N8N.
4. Após sucesso, um pop-up confirma que o relatório será enviado por email.

### Payload enviado ao N8N

```json
{
  "email": "usuario@sillion.com.br",
  "filename": "faturamento.xlsx",
  "file_base64": "UEsDBBQABgAIA...",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}
```

No N8N, no nó **Webhook** com método **POST**, basta acessar:
- `{{ $json.email }}` — email do remetente
- `{{ $json.filename }}` — nome original do arquivo
- `{{ $json.file_base64 }}` — conteúdo em base64 (decodificar com nó "Move Binary Data" ou expressão `Buffer.from(..., 'base64')`)
- `{{ $json.mime_type }}` — tipo MIME para reconstruir o arquivo

---

## Rodar localmente

```bash
# 1. Criar e ativar virtualenv (opcional, mas recomendado)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar
streamlit run app.py
```

O app abrirá em `http://localhost:8501`.

---

## Deploy no Streamlit Community Cloud

1. Crie um repositório no GitHub e suba estes arquivos:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`

2. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com a conta do GitHub.

3. Clique em **New app**, selecione o repositório, branch (geralmente `main`) e o arquivo principal (`app.py`).

4. Clique em **Deploy**. Em alguns minutos seu app estará no ar em uma URL pública.

> **Atenção:** apps no Streamlit Community Cloud são públicos por padrão. Se a URL do webhook N8N for sensível, não a deixe hardcoded — o app já pede a URL na UI, então cada usuário precisa saber qual webhook usar.

---

## Estrutura do projeto

```
Front Web Omie/
├── app.py              # App principal Streamlit
├── requirements.txt    # Dependências Python
├── .gitignore          # Arquivos ignorados pelo git
└── README.md           # Este arquivo
```

---

## Próximos passos (sugestões)

- Adicionar autenticação básica (Streamlit `st.login()` ou senha simples).
- Salvar histórico de envios em uma planilha ou banco.
- Permitir múltiplos arquivos em um único envio.
- Mostrar status do processamento no N8N (polling ou webhook de retorno).
