import io
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from starlette.datastructures import UploadFile as StarletteUploadFile

from app import MAX_SCAN_REQUEST_BODY_BYTES, MAX_UPLOAD_BYTES, app


def make_pdf(page_count=1, password=None):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    if password:
        writer.encrypt(password)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ScanFileSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.auth = {"X-KAVACH-Token": app.state.api_token}

    def tearDown(self):
        self.client.close()

    def upload(self, filename, content):
        return self.client.post(
            "/api/scan-file",
            headers=self.auth,
            files={"file": (filename, content)},
        )

    def test_total_request_body_limit_is_checked_before_multipart_parse(self):
        # Padding is outside the file part and pushes the whole request past its cap.
        boundary = "kavach-test-boundary"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"ok.txt\"\r\n"
            "Content-Type: text/plain\r\n\r\nhello\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"padding\"\r\n\r\n"
            + ("x" * MAX_SCAN_REQUEST_BODY_BYTES)
            + f"\r\n--{boundary}--\r\n"
        ).encode()
        response = self.client.post(
            "/api/scan-file",
            headers={**self.auth, "Content-Type": f"multipart/form-data; boundary={boundary}"},
            content=body,
        )
        self.assertEqual(response.status_code, 413)

    def test_oversized_file_is_rejected(self):
        response = self.upload("large.txt", b"a" * (MAX_UPLOAD_BYTES + 1))
        self.assertEqual(response.status_code, 413)
        self.assertIn("5 MB", response.json()["detail"])

    def test_malformed_pdf_is_rejected_without_parser_details(self):
        response = self.upload("broken.pdf", b"%PDF-1.7\nnot a real document")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Could not read this PDF. Try a valid, text-based PDF.",
        )

    def test_encrypted_pdf_is_rejected(self):
        response = self.upload("locked.pdf", make_pdf(password="test-password"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Password-protected PDFs are not supported.")

    def test_pdf_page_limit_is_preserved(self):
        response = self.upload("many-pages.pdf", make_pdf(page_count=21))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["detail"], "PDFs are limited to 20 pages.")

    def test_normal_pdf_scan_still_returns_masked_scan_result(self):
        sample_pdf = Path(__file__).resolve().parents[1] / "sample.pdf"
        response = self.upload("sample.pdf", sample_pdf.read_bytes())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page_count"], 1)
        self.assertIn("masked_text", response.json())
        self.assertIn("findings", response.json())

    def test_upload_is_closed_after_success(self):
        original_close = StarletteUploadFile.close
        close_calls = []

        async def tracked_close(upload):
            close_calls.append(True)
            await original_close(upload)

        with patch.object(StarletteUploadFile, "close", tracked_close):
            response = self.upload("note.txt", b"ordinary text")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(close_calls)

    def test_upload_is_closed_after_pdf_rejection(self):
        original_close = StarletteUploadFile.close
        close_calls = []

        async def tracked_close(upload):
            close_calls.append(True)
            await original_close(upload)

        with patch.object(StarletteUploadFile, "close", tracked_close):
            response = self.upload("broken.pdf", b"%PDF-1.7\ninvalid")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(close_calls)


if __name__ == "__main__":
    unittest.main()
