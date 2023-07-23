from enum import Enum
import mimetypes
class ContentType(Enum):
    HTML = "text/html"
    PLAIN = "text/plain"
    CSS = "text/css"
    JSON = "application/json"
    JAVASCRIPT = "application/javascript"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    XML = "application/xml"
    YAML = "application/x-yaml"
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    SVG = "image/svg+xml"
    MP4 = "video/mp4"
    MPEG = "video/mpeg"
    ZIP = "application/zip"

for c in ContentType:
    print(mimetypes.guess_extension('application/gzip'))