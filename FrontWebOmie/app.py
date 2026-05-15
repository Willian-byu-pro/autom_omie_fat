"""
Envio de faturamento — Front Streamlit
Encaminha arquivo (xlsx/xlsb/csv) + email para o backend N8N via POST JSON com base64.
"""

import base64
import re
import mimetypes
from datetime import datetime

import requests
import streamlit as st

# ---------- Config da página ----------
st.set_page_config(
    page_title="Envio de faturamento",
    page_icon="📤",
    layout="centered",
)

# ---------- Constantes ----------
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
TIPOS_ACEITOS = ["xlsx", "xlsb", "csv"]
TIMEOUT_REQ = 120  # segundos

MIME_FALLBACK = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsb": "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
    "csv": "text/csv",
}


# ---------- Helpers ----------
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


# ---------- UI ----------
st.title("📤 Envio de faturamento")
st.caption("Envie o arquivo de faturamento para processamento. O relatório retornará no seu email.")

st.divider()

webhook_url = st.secrets["N8N_WEBHOOK_URL"]

email = st.text_input(
    "Seu email",
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
    st.info(f"📎 **{arquivo.name}** — {tamanho_mb:.2f} MB")

st.write("")
enviar = st.button("Enviar", type="primary", use_container_width=True)

# ---------- Lógica de envio ----------
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
        with st.spinner("Enviando arquivo para o N8N..."):
            try:
                payload = montar_payload(email, arquivo)
                resp = enviar_para_n8n(webhook_url.strip(), payload)

                if 200 <= resp.status_code < 300:
                    # Pop-up de confirmação após sucesso
                    @st.dialog("✅ Envio realizado")
                    def confirmacao():
                        st.success("Arquivo enviado com sucesso!")
                        st.write(
                            f"O relatório processado será encaminhado para **{email.strip()}** "
                            "assim que o backend concluir o processamento."
                        )
                        st.caption(
                            f"Enviado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
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
