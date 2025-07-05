import streamlit as st
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader
from PIL import Image
import io
import tempfile # Importa a biblioteca para arquivos temporários
import os

def upload_evidence_photo(photo_file, id_equipamento, photo_type="nao_conformidade"):
    """
    Faz o upload de uma foto de evidência para o Google Drive com alta qualidade
    e retorna o link. Usa um arquivo temporário para garantir a compatibilidade.
    """
    if not photo_file:
        return None

    temp_file_path = None
    try:

        with Image.open(photo_file) as img:
            # 2. Converte para RGB para garantir compatibilidade
            if img.mode in ("RGBA", "P"):
                img_rgb = img.convert("RGB")
            else:
                img_rgb = img

            # 3. Cria um arquivo temporário nomeado com a extensão .jpg
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_f:
                temp_file_path = temp_f.name
                
                # 4. Salva a imagem processada neste arquivo temporário com alta qualidade
                img_rgb.save(temp_f, format='JPEG', quality=95)

        # 5. Agora temos um caminho de arquivo real para passar para o uploader
        uploader = GoogleDriveUploader()
        file_name = f"FOTO_{photo_type.upper()}_ID_{id_equipamento}_{date.today().isoformat()}.jpg"
        
        # A função de upload já sabe como lidar com um caminho de arquivo
        photo_link = uploader.upload_file_from_path(temp_file_path, file_name, "image/jpeg")
        
        st.success(f"Foto de evidência ({photo_type}) salva no Google Drive!")
        return photo_link
        
    except Exception as e:
        st.error(f"Falha ao processar ou fazer upload da foto de evidência: {e}")
        return None
    finally:
        # 6. Garante que o arquivo temporário seja removido, não importa o que aconteça
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
