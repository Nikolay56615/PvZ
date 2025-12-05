from fastapi import APIRouter, Depends, HTTPException
from ..deps import current_user
from ..schemas.tenants import (
    TenantCreateIn, GatewayCreateIn, BackendCreateIn, MoveGatewayIn, ToggleClientIn
)
from ..services.tenants import (
    create_tenant, delete_tenant, create_gateway_client, create_backend_client,
    move_gateway_to_tenant, disable_client, delete_client
)

router = APIRouter(prefix="/tenants", tags=["tenants"])

def _require_admin(user: dict):
    if user.get("permissions") not in {"ADMIN","OWNER"}:
        raise HTTPException(403, "Not enough permissions")

@router.post("/", summary="Создать тенант (роли + ACL)")
async def api_create_tenant(payload: TenantCreateIn, user=Depends(current_user)):
    _require_admin(user)
    return await create_tenant(payload.env, payload.tenant)

@router.delete("/{tenant}", summary="Удалить тенант (роли)")
async def api_delete_tenant(tenant: str, user=Depends(current_user)):
    _require_admin(user)
    return await delete_tenant(tenant)

@router.post("/gateways", summary="Создать шлюз-клиента и выдать роль тенанта")
async def api_create_gateway(payload: GatewayCreateIn, user=Depends(current_user)):
    _require_admin(user)
    return await create_gateway_client(payload.tenant, payload.client_id, payload.password)

@router.post("/backends", summary="Создать backend-клиента и выдать роль тенанта")
async def api_create_backend(payload: BackendCreateIn, user=Depends(current_user)):
    _require_admin(user)
    return await create_backend_client(payload.tenant, payload.username, payload.password)

@router.post("/gateways/move", summary="Перенести шлюз между тенантами")
async def api_move_gateway(payload: MoveGatewayIn, user=Depends(current_user)):
    _require_admin(user)
    return await move_gateway_to_tenant(payload.client_id, payload.old_tenant, payload.new_tenant)

@router.post("/clients/toggle", summary="Включить/выключить клиента")
async def api_toggle_client(payload: ToggleClientIn, user=Depends(current_user)):
    _require_admin(user)
    return await disable_client(payload.username, payload.disabled)

@router.delete("/clients/{username}", summary="Удалить клиента")
async def api_delete_client(username: str, user=Depends(current_user)):
    _require_admin(user)
    return await delete_client(username)
