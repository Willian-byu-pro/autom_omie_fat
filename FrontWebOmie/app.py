"""
Envio de faturamento — Front Streamlit (Sillion)
Encaminha arquivo (xlsx/xlsb/csv) + email para o backend N8N via POST JSON com base64.
"""

import base64
import re
import mimetypes
from datetime import datetime

import requests
import streamlit as st

# ============================================================
# Config da página
# ============================================================
st.set_page_config(
    page_title="Sillion · Envio de faturamento",
    page_icon="📤",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# Constantes
# ============================================================
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
TIPOS_ACEITOS = ["xlsx", "xlsb", "csv"]
TIMEOUT_REQ = 120  # segundos

MIME_FALLBACK = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsb": "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
    "csv": "text/csv",
}

# Paleta Sillion — preto/branco minimalista (extraído do site)
COR_PRIMARIA = "#0A0A0A"        # quase preto (botão, logo)
COR_PRIMARIA_HOVER = "#262626"  # cinza muito escuro (hover)
COR_TEXTO = "#0A0A0A"           # quase preto
COR_TEXTO_MUTED = "#737373"     # cinza médio (subtítulos)
COR_BORDA = "#E5E5E5"           # cinza claro
COR_BORDA_HOVER = "#A3A3A3"     # cinza médio
COR_FUNDO = "#FFFFFF"           # branco
COR_FUNDO_SUTIL = "#FAFAFA"     # branco quase imperceptível


# ============================================================
# CSS customizado
# ============================================================
CUSTOM_CSS = f"""
<style>
    /* Fonte Inter — sans-serif moderna que se aproxima do design */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Fundo branco limpo */
    .stApp {{
        background: {COR_FUNDO};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Esconde elementos padrão do Streamlit */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}

    /* Container principal */
    .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 2rem;
        max-width: 680px;
    }}

    /* Tipografia global */
    h1, h2, h3, h4, p, label, span, div, button {{
        font-family: 'Inter', sans-serif !important;
        color: {COR_TEXTO};
    }}

    /* ===== HEADER ===== */
    .brand-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    .brand-name {{
        font-size: 22px;
        font-weight: 700;
        color: {COR_TEXTO};
        letter-spacing: -0.02em;
    }}
    .brand-divider {{
        height: 1px;
        background: {COR_BORDA};
        margin: 24px 0 48px;
    }}

    /* ===== TÍTULO DA PÁGINA ===== */
    .page-title {{
        font-size: 44px;
        font-weight: 700;
        color: {COR_TEXTO};
        letter-spacing: -0.03em;
        line-height: 1.1;
        text-align: center;
        margin-bottom: 12px;
    }}
    .page-subtitle {{
        font-size: 16px;
        font-weight: 400;
        color: {COR_TEXTO_MUTED};
        text-align: center;
        max-width: 480px;
        margin: 0 auto 40px;
        line-height: 1.5;
    }}

    /* ===== CARD DO FORMULÁRIO ===== */
    /* Streamlit não tem um wrapper direto, então usamos pseudo-card via padding/border nos elementos */

    /* ===== INPUTS ===== */
    .stTextInput > div > div > input {{
        border-radius: 12px;
        border: 1px solid {COR_BORDA};
        padding: 14px 16px;
        font-size: 15px;
        font-family: 'Inter', sans-serif !important;
        background: {COR_FUNDO};
        transition: all 0.15s ease;
    }}
    .stTextInput > div > div > input:hover {{
        border-color: {COR_BORDA_HOVER};
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {COR_PRIMARIA};
        box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.06);
        outline: none;
    }}
    .stTextInput label, .stFileUploader label {{
        font-weight: 500 !important;
        font-size: 14px !important;
        color: {COR_TEXTO} !important;
        margin-bottom: 8px !important;
    }}

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] section {{
        border-radius: 12px;
        border: 1.5px dashed {COR_BORDA};
        background: {COR_FUNDO_SUTIL};
        padding: 24px;
        transition: all 0.15s ease;
    }}
    [data-testid="stFileUploader"] section:hover {{
        border-color: {COR_PRIMARIA};
        background: {COR_FUNDO};
    }}
    [data-testid="stFileUploader"] button {{
        background: {COR_FUNDO} !important;
        color: {COR_TEXTO} !important;
        border: 1px solid {COR_BORDA} !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }}
    [data-testid="stFileUploader"] button:hover {{
        border-color: {COR_PRIMARIA} !important;
    }}

    /* ===== BOTÃO PRIMÁRIO ===== */
    .stButton > button[kind="primary"] {{
        background: {COR_PRIMARIA};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 28px;
        font-weight: 600;
        font-size: 15px;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.15s ease;
        letter-spacing: -0.01em;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {COR_PRIMARIA_HOVER};
        transform: translateY(-1px);
    }}
    .stButton > button[kind="primary"]:active {{
        transform: translateY(0);
    }}
    .stButton > button[kind="primary"]:focus {{
        box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.12) !important;
    }}

    /* Botão secundário (OK do dialog) */
    .stButton > button[kind="secondary"] {{
        background: {COR_FUNDO};
        color: {COR_TEXTO};
        border: 1px solid {COR_BORDA};
        border-radius: 10px;
        font-weight: 500;
    }}

    /* ===== ALERTAS ===== */
    .stAlert {{
        border-radius: 12px;
        border: 1px solid {COR_BORDA};
        font-family: 'Inter', sans-serif !important;
    }}

    /* ===== PREVIEW DO ARQUIVO ===== */
    .file-preview {{
        background: {COR_FUNDO_SUTIL};
        border: 1px solid {COR_BORDA};
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 10px;
        font-size: 14px;
        color: {COR_TEXTO};
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .file-preview-icon {{
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: {COR_PRIMARIA};
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        flex-shrink: 0;
    }}

    /* ===== FOOTER ===== */
    .app-footer {{
        text-align: center;
        margin-top: 56px;
        padding-top: 28px;
        border-top: 1px solid {COR_BORDA};
        color: {COR_TEXTO_MUTED};
        font-size: 13px;
        font-weight: 400;
    }}
    .app-footer a {{
        color: {COR_TEXTO};
        text-decoration: none;
        font-weight: 500;
    }}
    .app-footer a:hover {{
        text-decoration: underline;
    }}

    /* ===== DIALOG (POP-UP) ===== */
    div[data-testid="stDialog"] > div {{
        border-radius: 16px !important;
        border: 1px solid {COR_BORDA} !important;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# Configuração segura: URL do webhook
# ============================================================
try:
    WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]
except (KeyError, FileNotFoundError):
    WEBHOOK_URL = None


# ============================================================
# Helpers
# ============================================================
def email_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def detectar_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in MIME_FALLBACK:
        return MIME_FALLBACK[ext]
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def montar_payload(email: str, arquivo) -> dict:
    conteudo = arquivo.getvalue()
    return {
        "email": email.strip(),
        "filename": arquivo.name,
        "file_base64": base64.b64encode(conteudo).decode("utf-8"),
        "mime_type": detectar_mime(arquivo.name),
    }


def enviar_para_n8n(url: str, payload: dict) -> requests.Response:
    return requests.post(
        url,
        json=payload,
        timeout=TIMEOUT_REQ,
        headers={"Content-Type": "application/json"},
    )


# ============================================================
# UI — Header
# ============================================================
st.markdown(
    """
    <div class="brand-header">
        <div class="brand-name">Sillion</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand-divider"></div>', unsafe_allow_html=True)

# ============================================================
# UI — Título e subtítulo
# ============================================================
st.markdown(
    '<div class="page-title">Envio de faturamento</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="page-subtitle">Envie o arquivo de faturamento para processamento automático. '
    'O relatório retornará no seu email.</div>',
    unsafe_allow_html=True,
)

# ============================================================
# Verificação de configuração
# ============================================================
if not WEBHOOK_URL:
    st.error(
        "⚠️ A URL do webhook N8N não foi configurada. "
        "Crie o arquivo `.streamlit/secrets.toml` com a chave `N8N_WEBHOOK_URL` "
        "ou configure-a no painel do Streamlit Community Cloud."
    )
    st.stop()

# ============================================================
# UI — Formulário
# ============================================================
email = st.text_input(
    "Email",
    placeholder="usuario@sillion.com.br",
    help="O relatório processado será enviado para este endereço.",
)

arquivo = st.file_uploader(
    "Arquivo de faturamento",
    type=TIPOS_ACEITOS,
    help="Formatos aceitos: .xlsx, .xlsb, .csv",
)

if arquivo is not None:
    tamanho_mb = len(arquivo.getvalue()) / (1024 * 1024)
    st.markdown(
        f'''
        <div class="file-preview">
            <div class="file-preview-icon">✓</div>
            <div><strong>{arquivo.name}</strong> · {tamanho_mb:.2f} MB</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

st.write("")
enviar = st.button("Enviar arquivo", type="primary", use_container_width=True)

# ============================================================
# Lógica de envio
# ============================================================
if enviar:
    erros = []

    if not email.strip():
        erros.append("Informe o email.")
    elif not email_valido(email):
        erros.append("Email inválido. Verifique o formato (ex: nome@dominio.com).")
    if arquivo is None:
        erros.append("Selecione um arquivo para enviar.")

    if erros:
        for e in erros:
            st.error(e)
    else:
        with st.spinner("Enviando arquivo para processamento..."):
            try:
                payload = montar_payload(email, arquivo)
                resp = enviar_para_n8n(WEBHOOK_URL, payload)

                if 200 <= resp.status_code < 300:
                    @st.dialog("Envio realizado")
                    def confirmacao():
                        st.success("Arquivo enviado com sucesso!")
                        st.write(
                            f"O relatório processado será encaminhado para "
                            f"**{email.strip()}** assim que o backend concluir "
                            "o processamento."
                        )
                        st.caption(
                            f"Enviado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                        )
                        if st.button("OK", use_container_width=True):
                            st.rerun()

                    confirmacao()
                else:
                    st.error(
                        f"O backend respondeu com status {resp.status_code}."
                    )
                    with st.expander("Detalhes da resposta"):
                        st.code(resp.text or "(sem corpo)")
            except requests.exceptions.Timeout:
                st.error("Tempo de resposta excedido. Verifique se o N8N está acessível.")
            except requests.exceptions.ConnectionError:
                st.error("Falha de conexão. Verifique a URL do webhook.")
            except Exception as exc:
                st.error(f"Erro inesperado: {exc}")

# ============================================================
# Footer
# ============================================================
st.markdown(
    f"""
    <div class="app-footer">
        © {datetime.now().year} <a href="https://www.sillion.com.br/" target="_blank">Sillion</a>
        · Plataforma interna de processamento
    </div>
    """,
    unsafe_allow_html=True,
)
