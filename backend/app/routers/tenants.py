from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from ..deps import current_user, db_conn
from ..schemas.tenants import (
    TenantCreateIn, GatewayCreateIn, BackendCreateIn, MoveGatewayIn, ToggleClientIn
)
from ..services.tenants import (
    create_tenant, delete_tenant, create_gateway_client, create_backend_client,
    move_gateway_to_tenant
)
from ..services.mosq_dynsec import DynSecError

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", summary="Список тенантов для пользователя")
async def api_list_tenants(user=Depends(current_user), conn: asyncpg.Connection = Depends(db_conn)):
    rows = await conn.fetch(
        "SELECT tenant_id::text, tenant_name AS name, tenant_owner AS description, created_at FROM iot.tenant WHERE tenant_owner = $1 OR tenant_id = (SELECT tenant_id FROM iot.users WHERE name = $1)",
        user.get('name')
    )
    return [dict(r) for r in rows]

def _require_admin(user: dict):
    if user.get("permissions") not in {"ADMIN","OWNER"}:
        raise HTTPException(403, "Not enough permissions")

@router.post("/", summary="Создать тенант (роли + ACL)")
async def api_create_tenant(payload: TenantCreateIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(db_conn)):
    tenant_name = payload.tenant
    tenant_id = await conn.fetchval("SELECT tenant_id::text FROM iot.tenant WHERE tenant_name = $1", tenant_name)
    
    if not tenant_id:
        tenant_id = await conn.fetchval(
            "INSERT INTO iot.tenant (tenant_name, tenant_owner) VALUES ($1, $2) RETURNING tenant_id::text",
            tenant_name, user.get('name')
        )
    else:
        if tenant_name != "fake":
            raise HTTPException(status_code=400, detail="Tenant already exists")
    # try:
        # result = await create_tenant(payload.env, tenant_name)
    # except DynSecError as e:
    #     result = {"tenant": tenant_name, "warning": "dynsec_failed", "detail": str(e)}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

    try:
        await conn.execute(
            "UPDATE iot.users SET tenant_id = $1, permissions = 'OWNER' WHERE name = $2",
            tenant_id, user.get('name')
        )
    except Exception:
        pass

    return {"tenant": tenant_name, "tenant_id": tenant_id}

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