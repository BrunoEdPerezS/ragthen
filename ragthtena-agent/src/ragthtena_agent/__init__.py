"""Raghtena Agent — CLI + backends for the Raghtena RAG system."""

from .backends.interface import Backend
from .backends.local import LocalBackend
from .backends.remote import RemoteBackend
