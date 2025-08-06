# 🔐 Como Gerar Chaves Secretas Seguras

## 📋 Chaves Necessárias

Para o deploy na Vercel, você precisa gerar duas chaves secretas:

1. **SECRET_KEY** - Chave secreta do Flask (para sessões, cookies, etc.)
2. **JWT_SECRET_KEY** - Chave secreta do JWT (para tokens de autenticação)

## 🛠️ Métodos para Gerar Chaves

### Método 1: Python (Recomendado)

```python
import secrets
import string

# Gerar chave secreta do Flask (32 bytes)
flask_secret = secrets.token_hex(32)
print(f"SECRET_KEY={flask_secret}")

# Gerar chave secreta do JWT (64 bytes)
jwt_secret = secrets.token_hex(64)
print(f"JWT_SECRET_KEY={jwt_secret}")

# Ou usando token_urlsafe para chaves mais longas
flask_secret_alt = secrets.token_urlsafe(32)
jwt_secret_alt = secrets.token_urlsafe(64)
print(f"\nAlternativo:")
print(f"SECRET_KEY={flask_secret_alt}")
print(f"JWT_SECRET_KEY={jwt_secret_alt}")
```

### Método 2: PowerShell

```powershell
# Gerar SECRET_KEY (32 bytes)
$secretKey = [System.Web.Security.Membership]::GeneratePassword(64, 10)
Write-Host "SECRET_KEY=$secretKey"

# Gerar JWT_SECRET_KEY (64 bytes)
$jwtKey = [System.Web.Security.Membership]::GeneratePassword(128, 20)
Write-Host "JWT_SECRET_KEY=$jwtKey"

# Ou usando .NET Crypto
Add-Type -AssemblyName System.Security
$rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$secretKey = [Convert]::ToBase64String($bytes)
Write-Host "SECRET_KEY=$secretKey"
```

### Método 3: Online (Use com Cuidado)

⚠️ **ATENÇÃO**: Apenas use geradores online confiáveis e nunca para produção crítica.

- [RandomKeygen](https://randomkeygen.com/)
- [AllKeys Generator](https://www.allkeysgenerator.com/)
- [Password Generator](https://passwordsgenerator.net/)

### Método 4: OpenSSL (Se disponível)

```bash
# SECRET_KEY (32 bytes)
openssl rand -hex 32

# JWT_SECRET_KEY (64 bytes)
openssl rand -hex 64

# Ou em base64
openssl rand -base64 32
openssl rand -base64 64
```

## 🔧 Script Automático Python

Crie um arquivo `gerar_chaves.py`:

```python
#!/usr/bin/env python3
import secrets
import os

def gerar_chaves():
    """Gera chaves secretas seguras para Flask e JWT"""
    
    print("🔐 Gerando chaves secretas seguras...\n")
    
    # Gerar chaves
    secret_key = secrets.token_hex(32)  # 256 bits
    jwt_secret_key = secrets.token_hex(64)  # 512 bits
    
    # Exibir chaves
    print("📋 Chaves geradas:")
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    
    # Salvar em arquivo .env.local
    env_content = f"""# Chaves secretas geradas automaticamente
# IMPORTANTE: Mantenha estas chaves seguras e não as compartilhe

SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret_key}

# Outras configurações
FLASK_ENV=production
FLASK_DEBUG=False
JWT_ACCESS_TOKEN_EXPIRES=24
LOG_LEVEL=INFO
CORS_ORIGINS=*
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
"""
    
    with open('.env.local', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Chaves salvas em .env.local")
    print("\n🚀 Para usar na Vercel:")
    print("1. Copie as chaves acima")
    print("2. Vá para o dashboard da Vercel")
    print("3. Acesse Settings > Environment Variables")
    print("4. Adicione cada chave como uma nova variável")
    
    print("\n⚠️  IMPORTANTE:")
    print("- Nunca compartilhe essas chaves")
    print("- Não as commite no Git")
    print("- Use chaves diferentes para desenvolvimento e produção")

if __name__ == "__main__":
    gerar_chaves()
```

## 🔒 Boas Práticas de Segurança

### ✅ Faça

- Use chaves com pelo menos 32 bytes (256 bits)
- Gere chaves diferentes para desenvolvimento e produção
- Use geradores criptograficamente seguros
- Mantenha as chaves em variáveis de ambiente
- Rotacione as chaves periodicamente

### ❌ Não Faça

- Não use chaves simples ou previsíveis
- Não commite chaves no código
- Não compartilhe chaves por email/chat
- Não reutilize chaves entre projetos
- Não use geradores online não confiáveis

## 🌐 Configurando na Vercel

### Passo a Passo:

1. **Acesse o Dashboard da Vercel**
   - Vá para [vercel.com/dashboard](https://vercel.com/dashboard)
   - Selecione seu projeto

2. **Acesse Environment Variables**
   - Clique em "Settings"
   - Clique em "Environment Variables"

3. **Adicione as Chaves**
   ```
   Name: SECRET_KEY
   Value: [sua-chave-secreta-do-flask]
   Environment: Production, Preview, Development
   
   Name: JWT_SECRET_KEY
   Value: [sua-chave-secreta-do-jwt]
   Environment: Production, Preview, Development
   ```

4. **Salve e Redeploy**
   - Clique em "Save"
   - Faça um novo deploy: `vercel --prod`

## 🔍 Verificando as Chaves

Para verificar se as chaves estão funcionando:

```python
# Teste simples
import os
from flask import Flask
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

jwt = JWTManager(app)

print("✅ Chaves carregadas com sucesso!")
print(f"SECRET_KEY: {'✅ Definida' if app.config['SECRET_KEY'] else '❌ Não definida'}")
print(f"JWT_SECRET_KEY: {'✅ Definida' if app.config['JWT_SECRET_KEY'] else '❌ Não definida'}")
```

## 📞 Troubleshooting

### Erro: "SECRET_KEY not set"
- Verifique se a variável está definida na Vercel
- Confirme o nome exato da variável
- Faça um redeploy após adicionar

### Erro: "JWT decode error"
- Verifique se JWT_SECRET_KEY está definida
- Confirme que a chave não mudou
- Limpe tokens existentes

### Chaves não funcionam
- Verifique se não há espaços extras
- Confirme que as chaves têm tamanho adequado
- Teste localmente primeiro

---

**💡 Dica**: Execute o script `gerar_chaves.py` para gerar suas chaves automaticamente!