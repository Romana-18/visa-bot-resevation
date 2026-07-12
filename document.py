import os
import requests
import json
import mimetypes
import logging

class Document:
    def __init__(self, doc_id, file_path):
        self.doc_id = doc_id
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.mime_type = f"image/{self.file_name.split('.')[(-1)]}"
        if self.file_name.split('.')[(-1)] == 'jpg':
            self.mime_type = 'image/jpeg'
        else:  # inserted
            if self.file_name.split('.')[(-1)] == 'pdf':
                self.mime_type = 'application/pdf'
        self.presignedUrl = ''
        self.temporaryKey = ''
        self.applicant = None

    def set_applicant(self, applicant):
        self.applicant = applicant

    def set_presigned_url(self, presigned_url):
        self.presignedUrl = presigned_url

    def set_temporary_key(self, temporary_key):
        self.temporaryKey = temporary_key

    def get_document_json(self):
        try:
            return {'documentTypeId': self.doc_id, 'temporaryKey': self.temporaryKey, 'fileName': self.file_name, 'fileSize': self.file_size, 'mimeType': self.mime_type}
        except Exception as e:
            return None

    def get_presigned_url_json(self):
        try:
            return {'fileSize': self.file_size, 'fileName': self.file_name, 'mimeType': self.mime_type}
        except Exception as e:
            return None

    def send_presigned_url_request(self, token, proxy):
        try:
            api_url = 'https://egyapi.almaviva-visa.it/reservation-manager//api/documents/v1/upload-presigned-url'
            headers = {'Accept': 'application/json, text/plain, */*', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
            data = self.get_presigned_url_json()
            response = requests.post(api_url, headers=headers, json=data, proxies=proxy)
            if response and response.status_code in [200, 201, 202, 203, 204]:
                self.set_presigned_url(response.json()['presignedUrl'])
                
                self.set_temporary_key(response.json()['temporaryKey'])

                print('Temporary Key:', self.temporaryKey)
                return True
        except Exception as e:
            return False
        else:  # inserted
            pass  # postinserted
        return False

    def send_put_request(self):
        try:
            api_url = self.presignedUrl
            with open(self.file_path, 'rb') as file:
                headers = {
                    'Content-Type': self.mime_type,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Origin': 'https://egy.almaviva-visa.it',
                    'Referer': 'https://egy.almaviva-visa.it/',
                    'Host': 'visasys.s3.eu-west-1.amazonaws.com'
                }
                response = requests.put(api_url, headers=headers, data=file)
            if response and response.status_code in [200, 201, 202, 203, 204]:
                return True
            else:
                return False
        except Exception as e:
            return False

    def upload_document(self, token, session):
        """Get temporary key and file info for the document and upload it."""
        logger = logging.getLogger(__name__)
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"❌ Image file not found: {self.file_path}")
                return None

            filename = os.path.basename(self.file_path)
            file_size = os.path.getsize(self.file_path)
            file_type, _ = mimetypes.guess_type(self.file_path)
            if not file_type:
                file_type = "application/octet-stream"

            # You may need to set self.base_api_url and self.access_token in your class
            upload_request_url = f"https://egyapi.almaviva-visa.it/reservation-manager/api/documents/v1/upload-presigned-url"
            payload = {"fileName": filename, "fileType": file_type}
            headers = {"Authorization": f"Bearer {token}"}
            logger.info(f"Requesting presigned URL for: {filename} from {upload_request_url}")
            url_resp = session.post(upload_request_url, headers=headers, json=payload)
            if url_resp.status_code != 200:
                logger.error(f"❌ Failed to get presigned upload URL: {url_resp.status_code}")
                return None

            upload_data = url_resp.json()
            temporary_key = upload_data.get("temporaryKey")
            print('templeeeey', temporary_key)
            presigned_url = upload_data.get("presignedUrl")
            if not temporary_key or not presigned_url:
                logger.error("❌ Temporary key or presigned URL not found in response")
                logger.error(f"Response data: {upload_data}")
                return None

            # Set the temporary key and presigned URL on the Document object
            self.set_temporary_key(temporary_key)
            self.set_presigned_url(presigned_url)

            # Upload the file to the presigned URL
            with open(self.file_path, "rb") as f:
                upload_headers = {"Content-Type": file_type}
                upload_resp = requests.put(presigned_url, data=f, headers=upload_headers)
                if upload_resp.status_code not in (200, 201):
                    logger.error(f"❌ Failed to upload file to storage: {upload_resp.status_code}")
                    return None

            logger.info(f"Temporary Key: {temporary_key}")
            return {
                "temporaryKey": temporary_key,
                "fileName": filename,
                "fileSize": file_size,
                "mimeType": file_type
            }
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
            return None