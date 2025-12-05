from .mosq_dynsec import dynsec_call, DynSecError

def _gateway_role_acls(env: str, tenant: str):
    base = f"{env}/{tenant}"
    return [
        {"acltype": "publishClientSend", "topic": f"{base}/sensors/+/humidity"},
        {"acltype": "publishClientSend", "topic": f"{base}/sensors/+/location"},
        {"acltype": "publishClientSend", "topic": f"{base}/sensors/+/state"},
        {"acltype": "publishClientSend", "topic": f"{base}/devices/+/ack"},
        {"acltype": "subscribePattern", "topic":  f"{base}/devices/+/command"},
    ]

def _backend_role_acls():
    return [
        {"acltype": "subscribePattern", "topic": "+/+/sensors/+/#"},
        {"acltype": "subscribePattern", "topic": "+/+/devices/+/ack"},
        {"acltype": "publishClientSend", "topic": "+/+/devices/+/command"},
    ]

async def create_tenant(env: str, tenant: str):
    gw_role = f"tenant:{tenant}:gateway"
    be_role = f"tenant:{tenant}:backend"

    cmds = [{"command": "createRole", "rolename": gw_role}]
    for acl in _gateway_role_acls(env, tenant):
        cmds.append({"command": "addRoleACL", "rolename": gw_role, **acl, "allow": True, "priority": 10})

    cmds.append({"command": "createRole", "rolename": be_role})
    for acl in _backend_role_acls():
        cmds.append({"command": "addRoleACL", "rolename": be_role, **acl, "allow": True, "priority": 10})

    return await dynsec_call(cmds)

async def delete_tenant(tenant: str):
    gw_role = f"tenant:{tenant}:gateway"
    be_role = f"tenant:{tenant}:backend"
    cmds = [
        {"command": "deleteRole", "rolename": gw_role},
        {"command": "deleteRole", "rolename": be_role},
    ]
    return await dynsec_call(cmds)

async def create_gateway_client(tenant: str, client_id: str, password: str):
    gw_role = f"tenant:{tenant}:gateway"
    cmds = [
        {"command": "createClient", "username": client_id, "clientid": client_id},
        {"command": "setClientPassword", "username": client_id, "password": password},
        {"command": "addClientRole", "username": client_id, "rolename": gw_role, "priority": 10},
    ]
    return await dynsec_call(cmds)

async def create_backend_client(tenant: str, username: str, password: str):
    be_role = f"tenant:{tenant}:backend"
    cmds = [
        {"command": "createClient", "username": username},
        {"command": "setClientPassword", "username": username, "password": password},
        {"command": "addClientRole", "username": username, "rolename": be_role, "priority": 10},
    ]
    return await dynsec_call(cmds)

async def move_gateway_to_tenant(client_id: str, old_tenant: str, new_tenant: str):
    cmds = [
        {"command": "removeClientRole", "username": client_id, "rolename": f"tenant:{old_tenant}:gateway"},
        {"command": "addClientRole",    "username": client_id, "rolename": f"tenant:{new_tenant}:gateway", "priority": 10},
    ]
    return await dynsec_call(cmds)

async def disable_client(username: str, disabled: bool = True):
    return await dynsec_call([{"command": "disableClient", "username": username, "disabled": disabled}])

async def delete_client(username: str):
    return await dynsec_call([{"command": "deleteClient", "username": username}])
