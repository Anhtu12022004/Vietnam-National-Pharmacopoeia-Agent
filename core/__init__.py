"""
core/ — Package chính của hệ thống PharmaRAG-VN.

Export hàm ask() để các module bên ngoài sử dụng dễ dàng.
"""

from core.chat_engine import ask

__all__ = ["ask"]
