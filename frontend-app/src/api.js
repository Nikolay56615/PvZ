const BASE = import.meta.env.VITE_API_BASE || 'http://5.129.192.139:8001'

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Accept': 'application/json' }
  if (body) headers['Content-Type'] = 'application/json'
  const authToken = token ?? localStorage.getItem('pvz_token')
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  const contentType = resp.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const data = isJson ? await resp.json() : null
  if (!resp.ok) {
    const msg = data?.detail || data || resp.statusText
    const err = new Error(msg)
    err.status = resp.status
    err.body = data
    throw err
  }
  return data
}

export const api = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  del: (path) => request(path, { method: 'DELETE' }),
}
