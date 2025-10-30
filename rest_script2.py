import streamlit as st
import os
from google.cloud import storage
from google.cloud import translate_v3 as translate
import logging
from streamlit_google_auth import Authenticate
from google.cloud import secretmanager
import tempfile
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting the App...")

# --- Function to get secret from Secret Manager ---
def get_secret(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")

# --- Google OAuth Configuration ---
PROJECT_ID = os.environ.get("PROJECT_ID", "63077862309")
SECRET_ID = "client_secrets"

# Fetch the secret and write it to a temporary file
client_secrets_content = get_secret(PROJECT_ID, SECRET_ID)

with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
    temp_file.write(client_secrets_content)
    SECRET_CREDENTIALS_PATH = temp_file.name

COOKIE_NAME = 'translation_hub_cookie'
COOKIE_KEY = os.environ.get("STREAMLIT_COOKIE_SECRET", "your_super_secret_cookie_key")
REDIRECT_URI = 'http://localhost:8501/'
COOKIE_EXPIRY_DAYS = 30

try:
    authenticator = Authenticate(
        secret_credentials_path=SECRET_CREDENTIALS_PATH,
        cookie_name=COOKIE_NAME,
        cookie_key=COOKIE_KEY,
        redirect_uri=REDIRECT_URI,
        cookie_expiry_days=COOKIE_EXPIRY_DAYS
    )

    # --- Authentication Flow ---
    authenticator.check_authentification()

    if not st.session_state.get('connected', False):
        st.title("Welcome to the Docs Translator App")
        st.write("Please log in to continue.")
        authorization_url = authenticator.get_authorization_url()
        st.link_button("Login with Google", authorization_url)
    else:
        st.sidebar.image(st.session_state['user_info'].get('picture'))
        st.sidebar.write(f"Hello, {st.session_state['user_info'].get('name')}!")
        st.sidebar.write(f"Email: {st.session_state['user_info'].get('email')}")

        if st.sidebar.button('Log out'):
            authenticator.logout()
            st.rerun()

        st.title("The Docs Translator app")

        TMP_BCKT = os.environ.get("TMP_BCKT", "translation_hub_tmp")
        LOCATION = os.environ.get("LOCATION", "us-central1")

        SUPPORTED_LANGUAGES = {
            "French": "fr",
            "English": "en",
            "Spanish": "es",
            "Italian": "it",
        }
        SUPPORTED_MIME_TYPES = {
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        if "data" not in st.session_state:
            st.session_state.data = None

        def get_lang_code(lang):
            return SUPPORTED_LANGUAGES.get(lang, None)

        def write_to_gcs(bucket_name, blob_name, data, storage_client):
            try:
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)

                with blob.open("wb") as f:
                    f.write(data)
                logger.info("File uploaded to gs://%s/%s", bucket_name, blob_name)
            except Exception as e:
                logger.error("Error uploading to GCS: %s", e)
                st.error(f"Error uploading to GCS: {e}")

        def delete_tmp(bkt_name,object, storage_client):
            try:
                bucket = storage_client.get_bucket(bkt_name)
                bucket.delete_blobs(blobs=list(bucket.list_blobs(prefix=object)))
                logger.info("Temporary files with prefix '%s' deleted from gs://%s", object, bkt_name)
            except Exception as e:
                logger.exception("Error deleting temp files: %s", e)
                raise ValueError("Error while deleteing temp files") from e

        file = st.file_uploader("Drag and drop file here", type=list(SUPPORTED_MIME_TYPES.keys()))
        src_lang = st.selectbox("Source Language:", list(SUPPORTED_LANGUAGES.keys()))
        dest_lang = st.selectbox("Destination Language:", list(SUPPORTED_LANGUAGES.keys()))

        if st.button("Translate"):
            logger.debug("Starting translation ...")
            if not file:
                st.error(f"Please choose a file")
            elif src_lang == dest_lang:
                st.error(f"Source and destination language cannot be the same.")
            else:
                with st.spinner("Translating file..."):
                    try:
                        dest_lang_code = get_lang_code(dest_lang)
                        src_lang_code = get_lang_code(src_lang)

                        storage_client = storage.Client()
                        translation_client = translate.TranslationServiceClient()

                        file_name, file_extension = os.path.splitext(file.name)
                        translated_file_name= f"{file_name}_{dest_lang_code}{file_extension}"
                        mime_type = SUPPORTED_MIME_TYPES.get(file_extension)

                        logger.debug("Upload src file to tmp bucket ...")
                        write_to_gcs(TMP_BCKT,f"{file_name}/{file.name}", file.getvalue(), storage_client)

                        logger.debug("Making API call ...")
                        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
                        
                        request = {
                            "parent": parent,
                            "source_language_code": src_lang_code,
                            "target_language_code": dest_lang_code,
                            "document_input_config": {
                                "gcs_source": {"input_uri": f"gs://{TMP_BCKT}/{file_name}/{file.name}"},
                                "mime_type": mime_type,
                            },
                            "document_output_config": {
                                "gcs_destination": {"output_uri_prefix": f"gs://{TMP_BCKT}/{file_name}/"}
                            },
                        }
                        response = translation_client.translate_document(request=request)
                        
                        logger.debug("Processing API response ...")
                        byte_stream = response.document_translation.byte_stream_outputs[0]
                        
                        st.session_state.data = (byte_stream, translated_file_name, mime_type)                
                        logger.debug("Delete tmp files ...")
                        delete_tmp(TMP_BCKT, file_name, storage_client)

                    except Exception as e:
                        logger.error("An error occurred during translation: %s", e, exc_info=True)
                        st.exception(f"An error occurred during translation: {e}")


        if st.session_state.data:
            st.download_button("Download Translated File", data=st.session_state.data[0], file_name=st.session_state.data[1], mime=st.session_state.data[2])

finally:
    # Clean up the temporary file
    if os.path.exists(SECRET_CREDENTIALS_PATH):
        os.remove(SECRET_CREDENTIALS_PATH)
