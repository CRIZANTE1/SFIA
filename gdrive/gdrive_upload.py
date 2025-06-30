import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import streamlit as st
import tempfile
from gdrive.config import get_credentials_dict, GDRIVE_FOLDER_ID, GDRIVE_SHEETS_ID

class GoogleDriveUploader:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self.credentials = None
        self.drive_service = None
        self.sheets_service = None
        self.initialize_services()

    def initialize_services(self):
        """Inicializa os serviços do Google Drive e Google Sheets"""
        try:
            credentials_dict = get_credentials_dict()
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=self.SCOPES
            )
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            st.error(f"Erro ao inicializar serviços do Google: {str(e)}")
            raise

    def upload_file(self, arquivo, novo_nome=None):
        """
        Faz upload do arquivo para o Google Drive
        """
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo.name)[1])
            temp_file.write(arquivo.getbuffer())
            temp_file.close()

            temp_path = temp_file.name

            file_metadata = {
                'name': novo_nome if novo_nome else arquivo.name,
                'parents': [GDRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(
                temp_path,
                mimetype=arquivo.type,
                resumable=True
            )
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            return file.get('webViewLink')

        except Exception as e:
            if "HttpError 404" in str(e) and GDRIVE_FOLDER_ID in str(e):
                st.error(f"Erro: A pasta do Google Drive com ID '{GDRIVE_FOLDER_ID}' não foi encontrada ou as permissões estão incorretas.")
            else:
                st.error(f"Erro ao fazer upload do arquivo: {str(e)}")
            raise
        finally:
            if temp_file and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e_remove:
                    st.error(f"Erro ao remover arquivo temporário '{temp_path}': {str(e_remove)}")

    def append_data_to_sheet(self, sheet_name, data_row):
        """
        Adiciona uma nova linha de dados à planilha do Google Sheets.
        """
        try:
            range_name = f"{sheet_name}!A:Z"
            body = {
                'values': [data_row]
            }
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=GDRIVE_SHEETS_ID,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            return result
        except Exception as e:
            st.error(f"Erro ao adicionar dados à planilha '{sheet_name}': {str(e)}")
            raise

    def get_data_from_sheet(self, sheet_name):
        """
        Lê todos os dados de uma aba específica da planilha do Google Sheets.
        """
        try:
            range_name = f"{sheet_name}!A:Z"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=GDRIVE_SHEETS_ID,
                range=range_name
            ).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha '{sheet_name}': {str(e)}")
            raise
