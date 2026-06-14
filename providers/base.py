from abc import ABC, abstractmethod


class BaseProvider(ABC):
    protocol: str

    @abstractmethod
    def create_client(self, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_client(self, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_client(self, name: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def list_clients(self) -> dict:
        raise NotImplementedError

    def health(self) -> dict:
        return {"status": "unknown"}
