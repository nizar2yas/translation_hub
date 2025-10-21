# Document Translator App

This Streamlit application provides a simple web interface to translate documents using the Google Cloud Translation API.

## Features

-   Translate documents between English, French, Spanish, and Italian.
-   Supports various document formats: `.doc`, `.docx`, `.pdf`, `.ppt`, `.pptx`, `.xls`, `.xlsx`.
-   Uses Google Cloud Storage for temporary file handling.
-   Securely authenticates using Application Default Credentials.
-   Includes instructions for local development and deployment to Google Cloud Run.

## Prerequisites

Before you begin, ensure you have the following installed:
-   [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
-   [Python 3.8+](https://www.python.org/downloads/)
-   [Docker](https://docs.docker.com/get-docker/)

## Configuration

The application requires the following Google Cloud project details, which are configured via environment variables:

-   `PROJECT_ID`: Your Google Cloud Project ID.
-   `TMP_BCKT`: The name of a Google Cloud Storage bucket for temporary file storage.
-   `LOCATION`: The Google Cloud region where your resources are located (e.g., `us-central1`).

The application is coded to use default values if these environment variables are not set, but configuring them is recommended.

## Local Development

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Authenticate with Google Cloud:**
    This command will open a browser window for you to log in and grant the SDK access to your Google Cloud account. The credentials will be stored locally and used by the application automatically.
    ```bash
    gcloud auth application-default login
    ```

5.  **Set environment variables:**
    Replace the placeholder values with your actual project details.
    ```bash
    export PROJECT_ID="your-gcp-project-id"
    export TMP_BCKT="your-gcs-bucket-name"
    export LOCATION="your-gcp-region"
    ```

6.  **Run the application:**
    ```bash
    streamlit run rest_script2.py
    ```
    The application will be available at `http://localhost:8501`.

## Deployment to Google Cloud Run

1.  **Enable APIs:**
    Ensure you have the Cloud Translation API, Cloud Build API, and Cloud Run API enabled in your GCP project.

2.  **Create a Service Account:**
    It is best practice to run your service with a dedicated service account with the minimum necessary permissions.
    -   Go to the IAM & Admin section in the Google Cloud Console and create a new service account.
    -   Grant this service account the following roles:
        -   `Cloud Translation API User`
        -   `Storage Object Admin` (for the temporary bucket)

3.  **Build the Container Image:**
    Use Cloud Build to build your container image and push it to Google Container Registry. This command uses your active gcloud project configuration for the project ID.
    ```bash
    gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/translation-app
    ```

4.  **Deploy to Cloud Run:**
    Deploy your container image to Cloud Run. Remember to replace placeholders and set the environment variables.
    ```bash
    gcloud run deploy translation-app \
      --image gcr.io/$(gcloud config get-value project)/translation-app \
      --platform managed \
      --region [YOUR_GCP_REGION] \
      --service-account [YOUR_SERVICE_ACCOUNT_EMAIL] \
      --set-env-vars="PROJECT_ID=$(gcloud config get-value project)" \
      --set-env-vars="TMP_BCKT=[YOUR_GCS_BUCKET_NAME]" \
      --set-env-vars="LOCATION=[YOUR_GCP_REGION]" \
      --allow-unauthenticated
    ```
    -   `[YOUR_GCP_REGION]`: e.g., `us-central1`
    -   `[YOUR_SERVICE_ACCOUNT_EMAIL]`: The email of the service account you created.
    -   `[YOUR_GCS_BUCKET_NAME]`: The name of your temporary GCS bucket.

    The command will output a URL where your service is accessible.