
from abc import ABC, abstractmethod


class DataLakeBase(ABC):  # extends Abstract Base class

    @abstractmethod
    def upload(self, bucket_path: str, local_path: str, bucket_name: str = None) -> bool:
        pass

    @abstractmethod
    def upload_string(self, bucket_path: str, string: str, bucket_name: str = None) -> bool:
        pass

    @abstractmethod
    def download(self, bucket_path: str, destination_local_path: str, bucket_name: str = None) -> bool:
        pass

    @abstractmethod
    def download_string(self, bucket_path: str, bucket_name: str = None) -> str:
        pass
