import io
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytest

from app.channels.email import EmailAdapter
from app.utils.email_parser import extract_attachments


def _build_email() -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["Subject"] = "Тест"
    msg.attach(MIMEText("Привет", "plain", "utf-8"))
    att = MIMEApplication(b"\x00\x01\x02payload-data", "octet-stream")
    att.add_header("Content-Disposition", "attachment", filename="report.pdf")
    msg.attach(att)
    return msg


def test_extract_attachments_saves_file(tmp_path):
    msg = _build_email()
    result = extract_attachments(msg, tmp_path)

    assert len(result) == 1
    entry = result[0]
    assert entry["file_name"] == "report.pdf"
    assert entry["mime_type"] == "application/octet-stream"
    assert entry["file_size"] == len(b"\x00\x01\x02payload-data")

    saved = tmp_path / entry["file_path"]
    assert saved.is_file()
    assert saved.read_bytes() == b"\x00\x01\x02payload-data"


def test_extract_attachments_encoded_filename(tmp_path):
    msg = MIMEMultipart()
    msg.attach(MIMEText("Body", "plain", "utf-8"))
    att = MIMEApplication(b"data", "octet-stream")
    att.add_header("Content-Disposition", "attachment", filename="=?utf-8?B?0YHQv9C40YHQvtC6LnR4dA==?=")
    msg.attach(att)

    result = extract_attachments(msg, tmp_path)
    assert len(result) == 1
    assert result[0]["file_name"] == "список.txt"


def test_extract_attachments_no_attachments(tmp_path):
    msg = MIMEText("Просто текст", "plain", "utf-8")
    assert extract_attachments(msg, tmp_path) == []


def test_extract_attachments_multiple(tmp_path):
    msg = MIMEMultipart()
    msg.attach(MIMEText("Body", "plain", "utf-8"))
    for i, name in enumerate(["a.png", "b.docx"]):
        att = MIMEApplication(b"x" * 10, "octet-stream")
        att.add_header("Content-Disposition", "attachment", filename=name)
        msg.attach(att)

    result = extract_attachments(msg, tmp_path)
    assert len(result) == 2
    assert {e["file_name"] for e in result} == {"a.png", "b.docx"}


@pytest.mark.asyncio
async def test_download_file_returns_bytesio(tmp_path, monkeypatch):
    import app.channels.email as email_mod

    monkeypatch.setattr(email_mod, "_DATA_DIR", tmp_path)
    (tmp_path / "attachments").mkdir()
    (tmp_path / "attachments" / "abc.pdf").write_bytes(b"file-content")

    adapter = EmailAdapter()
    data = await adapter.download_file("attachments/abc.pdf")
    assert isinstance(data, io.BytesIO)
    data.seek(0)
    assert data.read() == b"file-content"


@pytest.mark.asyncio
async def test_download_file_missing_raises(tmp_path, monkeypatch):
    import app.channels.email as email_mod

    monkeypatch.setattr(email_mod, "_DATA_DIR", tmp_path)
    adapter = EmailAdapter()
    with pytest.raises(FileNotFoundError):
        await adapter.download_file("attachments/missing.pdf")


@pytest.mark.asyncio
async def test_download_file_empty_path_raises(tmp_path, monkeypatch):
    import app.channels.email as email_mod

    monkeypatch.setattr(email_mod, "_DATA_DIR", tmp_path)
    adapter = EmailAdapter()
    with pytest.raises(ValueError):
        await adapter.download_file(None)
