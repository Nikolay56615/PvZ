from pydantic import BaseModel, Field

class TenantCreateIn(BaseModel):
    env: str = Field(examples=["dev","prod"])
    tenant: str = Field(examples=["alpha"])

class GatewayCreateIn(BaseModel):
    tenant: str
    client_id: str
    password: str

class BackendCreateIn(BaseModel):
    tenant: str
    username: str
    password: str

class MoveGatewayIn(BaseModel):
    client_id: str
    old_tenant: str
    new_tenant: str

class ToggleClientIn(BaseModel):
    username: str
    disabled: bool = True
