from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from auth.security import normalizar_cpf, validar_cpf


class Role(str, Enum):
    admin = "admin"
    usuario = "usuario"


class UserRecord(BaseModel):
    cpf: str
    role: Role
    nome: Optional[str] = None
    ativo: bool = True


class LoginRequest(BaseModel):
    cpf: str
    senha: str

    @field_validator("cpf")
    @classmethod
    def cpf_valido(cls, v: str) -> str:
        cpf = normalizar_cpf(v)
        if not validar_cpf(cpf):
            raise ValueError("CPF inválido")
        return cpf


class UserCreate(BaseModel):
    cpf: str
    senha: str = Field(min_length=6)
    nome: Optional[str] = None
    role: Role = Role.usuario

    @field_validator("cpf")
    @classmethod
    def cpf_valido(cls, v: str) -> str:
        cpf = normalizar_cpf(v)
        if not validar_cpf(cpf):
            raise ValueError("CPF inválido")
        return cpf


class UserUpdate(BaseModel):
    nome: Optional[str] = None
    senha: Optional[str] = Field(default=None, min_length=6)
    role: Optional[Role] = None
    ativo: Optional[bool] = None


class UserPublic(BaseModel):
    cpf: str
    role: Role
    nome: Optional[str] = None
    ativo: bool
    created_at: str
