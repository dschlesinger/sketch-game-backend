from typing import Annotated

from files.s3 import S3Storage
from files.local import LocalStorage

Storage = S3Storage | LocalStorage