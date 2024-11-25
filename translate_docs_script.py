import functions_framework
import os
from google.cloud import storage
from google.cloud import translate_v3beta1 as translate

# Triggered by a change in a storage bucket


def hello_gcs(cloud_event):
    INPUT_BUCKET = "docs_input"
    OUTPUT_BUCKET = "docs_output"
    ERROR_BUCKET = "docs_error"
    PROJECT_ID = "swo-trabajo-yrakibi"
    data = cloud_event.data
    name = data["name"]
    filename, file_extension = os.path.splitext(name)
    src_lang = filename[-2:]
    dest_langs = ["en"]

    if not file_extension in ['.doc', '.docx', '.pdf', '.ppt', '.pptx', '.xls', '.xlsx']:
        move_blob(INPUT_BUCKET, name, ERROR_BUCKET)
        raise Exception(
            "Only those extensions are supported : .doc, .docx, .pdf, .ppt, .pptx, .xls, .xlsx")

    if not is_valid_language(src_lang):
        move_blob(INPUT_BUCKET, name, ERROR_BUCKET)
        raise Exception(
            "Error valide languages are : 'fr', 'it', 'es', which should be included at the end of the file ex: my_file_fr.pdf")

    # mime_type = get_mime_type(file_extension)
    file_path = f"gs://{INPUT_BUCKET}/{name}"
    output_uri = f"gs://{OUTPUT_BUCKET}/{filename}/"
    batch_translate_document(file_path, output_uri,
                             PROJECT_ID, src_lang, dest_langs)


def batch_translate_document(input_uri, output_uri, project_id, src_lang, dest_langs) -> translate.BatchTranslateDocumentResponse:
    client = translate.TranslationServiceClient()

    location = "us-central1"

    gcs_source = {"input_uri": input_uri}
    gcs_destination = {"output_uri_prefix": output_uri}

    batch_document_input_configs = {
        "gcs_source": gcs_source,
    }
    batch_document_output_config = {"gcs_destination": gcs_destination}

    parent = f"projects/{project_id}/locations/{location}"

    operation = client.batch_translate_document(
        request={
            "parent": parent,
            "source_language_code": src_lang,
            "target_language_codes": dest_langs,
            "input_configs": [batch_document_input_configs],
            "output_config": batch_document_output_config,
        }
    )

    print("Waiting for operation to complete...")
    response = my_callback(operation)
    print(f"Total Pages: {response.total_pages}")
    return response


def move_blob(bucket_name, file_name, destination_bucket_name):
    storage_client = storage.Client()

    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(file_name)
    destination_bucket = storage_client.bucket(destination_bucket_name)

    destination_generation_match_precondition = 0

    source_bucket.copy_blob(source_blob, destination_bucket, file_name, if_generation_match=destination_generation_match_precondition,
                            )
    source_bucket.delete_blob(file_name)


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


def is_valid_language(lang):
    if lang.lower() in ['fr', 'en', 'it']:
        return True
    else:
        return False


def my_callback(future):
    result = future.result()
    print("done")
    return result


class Event:
    def __init__(self, data, event_type, specversion, source, event_id):
        self.data = data
        self.type = event_type
        self.specversion = specversion
        self.source = source
        self.id = event_id


event = Event(
    data={
        "name": "test_fr.pdf",
        "bucket": "docs_input",
        "contentType": "application/json",
        "metageneration": "1",
        "timeCreated": "2020-04-23T07:38:57.230Z",
        "updated": "2020-04-23T07:38:57.230Z"
    },
    event_type="google.cloud.storage.object.v1.finalized",
    specversion="1.0",
    source="//pubsub.googleapis.com/",
    event_id="1234567890"
)

hello_gcs(event)
