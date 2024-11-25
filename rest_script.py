import streamlit as st
import requests
import json
import base64
import os
import time
from google.cloud import storage


st.title("The Docs Translator app")


def get_lang_code(lang):
    match(lang):
        case "French":
            return "fr"
        case "English":
            return "en"
        case "Spanish":
            return "es"
        case "Italien":
            return "it"
        case _:
            raise Exception(
                "Only French, English, Spanish and Italien languages are supported")

def get_mime_type(type):
    match(type):
        case ".doc":
            return "application/msword"
        case ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        case ".pdf":
            return "application/pdf"
        case ".ppt":
            return "application/vnd.ms-powerpoint"
        case ".pptx":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        case ".xls":
            return "application/vnd.ms-excel"
        case ".xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        case _:
            raise Exception(f"extension : {type} not supported, here are the supported ones: .doc, .docx, .pdf, .ppt, .pptx, .xls, .xlsx")

def is_same_lang(lang1,lang2):
    if lang1 == lang2:
        return True
    else:
        return False

file = st.file_uploader(label="Drag and drop file here", type=[
                        'pdf', 'doc', 'docx', 'ppt', 'pptx'])
src_lang = st.selectbox("What is the file original language ?",
                        ("French", "English", "Spanish", "Italien"))
dest_lang = st.selectbox("What is the destination language ?",
                         ("French", "English", "Spanish", "Italien"))
submit = st.button("Submit")

if is_same_lang(src_lang, dest_lang):
    st.exception(f"Source and destination language cannot be the same.")

def write_to_gcs(bucket_name, blob_name,data):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("wb") as f:
        f.write(data)

# def is_file_already_translated(file_name):


if file and src_lang and dest_lang and submit:
    with st.spinner("Translating file..."):
        write_to_gcs("docs_input",file.name, file.getvalue())
        print("Enter")
        src_lang_code = get_lang_code(src_lang)
        dest_lang_code = get_lang_code(dest_lang)

        url = "https://translation.googleapis.com/v3/projects/swo-trabajo-yrakibi/locations/us-central1:translateDocument"

        file_name, file_extension = os.path.splitext(file.name)
        translated_file_name= f"{file_name}_{dest_lang_code}.{file_extension}"

        payload = json.dumps({
            "source_language_code": src_lang_code,
            "target_language_code": dest_lang_code,
            "document_input_config": {
                "gcsSource": {
                    "inputUri": f"gs://docs_input/{file.name}"
                }
            },
            "document_output_config": {
                "gcsDestination": {
                    "outputUriPrefix": f"gs://docs_output/{file_name}_{dest_lang_code}/"
                }
            }
        })

        headers = {
            'x-goog-user-project': 'swo-trabajo-yrakibi',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ya29.a0AeDClZDl4Ud5OTQQwLTtT0LsrLjbdLKUJZPDxdFYNJF2WpXR_QUeH5Au5riqZ5ZQPeEBlDMPUZmx0HHqbVKfNQ5Ke8keyVdN757UAznQ1unvs_rAaG11HQsfT2Ar9jh42_TYySSsMaj-vTdRHOeSIfX8aMZggUrxQYSrTsTanRoZVBgaCgYKAdASARASFQHGX2MioV-ESdW2TVr2T999YLYNjQ0182'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        time.sleep(1)
        if response.status_code == 200:
            mime_type=get_mime_type(file_extension)
            resp_json = json.loads(response.text)
            byte_stream = base64.b64decode( resp_json["documentTranslation"]["byteStreamOutputs"][0])
            st.download_button(label="download translated file", data=byte_stream, file_name=translated_file_name, mime=mime_type)
        else:
            st.exception(f"Error while calling the api : \n {response.text}")
