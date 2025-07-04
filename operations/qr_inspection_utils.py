import cv2
import numpy as np
import pandas as pd

def decode_qr_from_image(image_file):
    """
    Decodifica o QR code, aplicando pré-processamento para melhorar a detecção.
    Retorna o ID do Equipamento e o Selo (se houver).
    """
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return None, None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)

        # Inicializa o detector
        detector = cv2.QRCodeDetector()
        
        # Tenta decodificar a imagem processada
        decoded_text, _, _ = detector.detectAndDecode(thresh)

        # Se falhar na imagem processada, tenta na imagem original em tons de cinza
        if not decoded_text:
            decoded_text, _, _ = detector.detectAndDecode(gray)

        # Se ainda falhar, tenta na imagem colorida original como último recurso
        if not decoded_text:
            decoded_text, _, _ = detector.detectAndDecode(img)
            
        if not decoded_text:
            return None, None
        
        # Lógica de extração (permanece a mesma)
        decoded_text = decoded_text.strip()
        if '#' in decoded_text:
            parts = decoded_text.split('#')
            if len(parts) >= 4:
                id_equipamento = parts[3].strip()
                selo_inmetro = None
                return id_equipamento, selo_inmetro
            return None, None
        else:
            id_equipamento = decoded_text
            selo_inmetro = None
            return id_equipamento, selo_inmetro
            
    except Exception:
        return None, None

def find_last_record_from_history(df_history, search_value, column_name):
    """
    Função genérica para encontrar o último registro em um DataFrame de histórico.
    """
    if df_history.empty or column_name not in df_history.columns: 
        return None
        
    records = df_history[df_history[column_name].astype(str) == str(search_value)].copy()
    
    if records.empty: 
        return None
        
    records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
    records.dropna(subset=['data_servico'], inplace=True)
    
    if records.empty: 
        return None
        
    return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
