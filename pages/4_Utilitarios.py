import streamlit as st
import qrcode
from PIL import Image
import io
import zipfile
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def generate_qr_code_image(data):
    """
    Gera uma imagem de QR Code a partir de um dado.
    Retorna um objeto de imagem do Pillow.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def image_to_bytes(img: Image.Image):
    """
    Converte um objeto de imagem do Pillow para bytes.
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def show_utilities_page():
    st.title("🛠️ Utilitários do Sistema")
    st.header("Gerador de QR Codes para Selos INMETRO")

    st.info(
        "Digite ou cole uma lista de números de Selo INMETRO, um por linha. "
        "O sistema irá gerar um QR Code para cada selo, pronto para download e impressão."
    )

    # Área de texto para inserir os selos
    selo_texts = st.text_area(
        "Insira os números dos Selos INMETRO (um por linha):",
        height=250,
        placeholder="21769\n20899\n16019\n..."
    )

    if selo_texts:
        # Processa a entrada: remove linhas vazias e espaços extras
        selo_list = [selo.strip() for selo in selo_texts.split('\n') if selo.strip()]

        if selo_list:
            st.subheader("Pré-visualização dos QR Codes Gerados")
            
            # Cria colunas para exibir os QR codes
            cols = st.columns(3)
            generated_images = {} # Dicionário para armazenar imagens geradas {selo: img_bytes}

            for i, selo in enumerate(selo_list):
                with cols[i % 3]:
                    st.markdown(f"**Selo: `{selo}`**")
                    qr_img = generate_qr_code_image(selo)
                    st.image(qr_img, width=200)
                    
                    # Converte a imagem para bytes para o download
                    img_bytes = image_to_bytes(qr_img)
                    generated_images[selo] = img_bytes

                    # Adiciona um botão de download individual
                    st.download_button(
                        label="Baixar PNG",
                        data=img_bytes,
                        file_name=f"qrcode_selo_{selo}.png",
                        mime="image/png",
                        key=f"download_{selo}"
                    )
            
            st.markdown("---")
            st.subheader("Baixar Todos os QR Codes")

            # Cria um arquivo ZIP em memória
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for selo, img_bytes in generated_images.items():
                    zip_file.writestr(f"qrcode_selo_{selo}.png", img_bytes)
            
            st.download_button(
                label="📥 Baixar Todos como .ZIP",
                data=zip_buffer.getvalue(),
                file_name="qrcodes_extintores.zip",
                mime="application/zip",
                use_container_width=True
            )

# --- Boilerplate de Autenticação ---
if not show_login_page():
    st.stop()

show_user_header()
show_logout_button()

# Esta página só deve ser acessível para administradores
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_utilities_page()
else:
    st.sidebar.error("🔒 Acesso restrito")
    st.warning("Você não tem permissão para acessar esta página.")
    st.info("A geração de QR Codes é uma funcionalidade restrita a administradores.")
