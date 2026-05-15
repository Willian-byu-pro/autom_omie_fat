"""
Envio de faturamento — Front Streamlit (Sillion)
Encaminha arquivo (xlsx/xlsb/csv) + email para o backend N8N via POST JSON com base64.
"""

import base64
import re
import mimetypes
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

# ============================================================
# Config da página
# ============================================================
st.set_page_config(
    page_title="Sillion · Envio de faturamento",
    page_icon="",
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

CSS_PATH = Path(__file__).parent / "styles" / "main.css"


# ============================================================
# Carrega o CSS externo + meta tag anti-tradução
# ============================================================
def carregar_css(caminho: Path) -> None:
    """Lê o arquivo CSS e injeta na página via st.markdown."""
    try:
        css = caminho.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo de estilos não encontrado: {caminho}")


# Desativa Google Translate nesta página (evita bug com ícones Material)
st.markdown(
    '<meta name="google" content="notranslate">'
    '<meta http-equiv="Content-Language" content="pt-br">',
    unsafe_allow_html=True,
)

carregar_css(CSS_PATH)


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
