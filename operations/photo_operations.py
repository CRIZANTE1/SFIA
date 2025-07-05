# operations/photo_operations.py

import streamlit as st
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader
from PIL import Image
import io #

def upload_evidence_photo(photo_file, id_equipamento, photo_type="nao_conformidade"):
    """
    Faz o upload de uma foto de evidência para o Google Drive com alta qualidade
    e retorna o link.
    """
    if not photo_file:
        return None

    try:
        img = Image.open(photo_file)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        

        uploader = GoogleDriveUploader()
        file_name = f"FOTO_{photo_type.upper()}_ID_{id_equipamento}_{date.today().isoformat()}.jpg"
        
        class InMemoryFile:
            def __init__(self, name, buffer, mime_type):
                self.name = name
                self.getbuffer = buffer.getvalue
                self.type = mime_type
        
        in_memory_file = InMemoryFile(file_name, img_buffer, "image/jpeg")

        photo_link = uploader.upload_file(in_memory_file, novo_nome=file_name)
        st.success(f"Foto de evidência ({photo_type}) salva no Google Drive!")
        return photo_link
        
    except Exception as e:
        st.error(f"Falha ao processar ou fazer upload da foto de evidência: {e}")
        return None
