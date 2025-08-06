#!/usr/bin/env python3
"""
Script para gerar chaves secretas seguras para Flask e JWT
Uso: python gerar_chaves.py
"""

import secrets
import os
from datetime import datetime

def gerar_chaves():
    """Gera chaves secretas seguras para Flask e JWT"""
    
    print("🔐 Gerando chaves secretas seguras...\n")
    
    # Gerar chaves usando secrets (criptograficamente seguro)
    secret_key = secrets.token_hex(32)  # 256 bits
    jwt_secret_key = secrets.token_hex(64)  # 512 bits
    
    # Gerar chaves alternativas em base64
    secret_key_b64 = secrets.token_urlsafe(32)
    jwt_secret_key_b64 = secrets.token_urlsafe(64)
    
    # Exibir chaves
    print("📋 Chaves geradas (HEX):")
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    
    print("\n📋 Chaves alternativas (Base64):")
    print(f"SECRET_KEY={secret_key_b64}")
    print(f"JWT_SECRET_KEY={jwt_secret_key_b64}")
    
    # Criar conteúdo do arquivo .env
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    env_content = f"""# Chaves secretas geradas automaticamente em {timestamp}
# IMPORTANTE: Mantenha estas chaves seguras e não as compartilhe
# NUNCA commite este arquivo no Git!

# Chaves principais (use estas na Vercel)
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret_key}

# Configurações do Flask
FLASK_ENV=production
FLASK_DEBUG=False

# Configurações do JWT
JWT_ACCESS_TOKEN_EXPIRES=24

# Configurações de Log
LOG_LEVEL=INFO

# Configurações de CORS
CORS_ORIGINS=*

# Configurações de Sessão
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Banco de Dados (configure conforme necessário)
# DATABASE_URL=postgresql://username:password@host:port/database
DATABASE_URL=sqlite:///trading_bot.db

# Configurações da IQ Option (se necessário)
# IQ_OPTION_EMAIL=seu-email@exemplo.com
# IQ_OPTION_PASSWORD=sua-senha
"""
    
    # Salvar em arquivo .env.local
    try:
        with open('.env.local', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("\n✅ Chaves salvas em .env.local")
    except Exception as e:
        print(f"\n❌ Erro ao salvar arquivo: {e}")
    
    # Criar arquivo de backup com timestamp
    backup_filename = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(backup_filename, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ Backup salvo em {backup_filename}")
    except Exception as e:
        print(f"❌ Erro ao salvar backup: {e}")
    
    # Instruções para uso
    print("\n🚀 Para usar na Vercel:")
    print("1. Copie as chaves HEX mostradas acima")
    print("2. Vá para https://vercel.com/dashboard")
    print("3. Selecione seu projeto")
    print("4. Acesse Settings > Environment Variables")
    print("5. Adicione cada chave como uma nova variável:")
    print("   - Name: SECRET_KEY")
    print("   - Value: [cole a chave SECRET_KEY]")
    print("   - Environment: Production, Preview, Development")
    print("   ")
    print("   - Name: JWT_SECRET_KEY")
    print("   - Value: [cole a chave JWT_SECRET_KEY]")
    print("   - Environment: Production, Preview, Development")
    print("6. Clique em Save")
    print("7. Faça um novo deploy: vercel --prod")
    
    print("\n⚠️  IMPORTANTE - Segurança:")
    print("- ❌ NUNCA compartilhe essas chaves")
    print("- ❌ NÃO as commite no Git")
    print("- ❌ NÃO as envie por email/chat")
    print("- ✅ Use chaves diferentes para desenvolvimento e produção")
    print("- ✅ Rotacione as chaves periodicamente")
    print("- ✅ Mantenha backups seguros")
    
    print("\n📁 Arquivos criados:")
    print("- .env.local (para uso local)")
    print(f"- {backup_filename} (backup com timestamp)")
    
    print("\n🔍 Para testar as chaves localmente:")
    print("python -c \"import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print('SECRET_KEY:', '✅' if os.getenv('SECRET_KEY') else '❌'); print('JWT_SECRET_KEY:', '✅' if os.getenv('JWT_SECRET_KEY') else '❌')\"")

def verificar_chaves():
    """Verifica se as chaves estão definidas"""
    print("🔍 Verificando chaves existentes...\n")
    
    # Verificar variáveis de ambiente
    secret_key = os.getenv('SECRET_KEY')
    jwt_secret_key = os.getenv('JWT_SECRET_KEY')
    
    print(f"SECRET_KEY: {'✅ Definida' if secret_key else '❌ Não definida'}")
    print(f"JWT_SECRET_KEY: {'✅ Definida' if jwt_secret_key else '❌ Não definida'}")
    
    if secret_key:
        print(f"Tamanho SECRET_KEY: {len(secret_key)} caracteres")
    if jwt_secret_key:
        print(f"Tamanho JWT_SECRET_KEY: {len(jwt_secret_key)} caracteres")
    
    # Verificar arquivo .env.local
    if os.path.exists('.env.local'):
        print("\n📁 Arquivo .env.local encontrado")
        try:
            with open('.env.local', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'SECRET_KEY=' in content:
                    print("✅ SECRET_KEY encontrada no arquivo")
                if 'JWT_SECRET_KEY=' in content:
                    print("✅ JWT_SECRET_KEY encontrada no arquivo")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
    else:
        print("\n📁 Arquivo .env.local não encontrado")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'verificar':
        verificar_chaves()
    else:
        gerar_chaves()
        
    print("\n" + "="*60)
    print("Script concluído! 🎉")
    print("Para verificar as chaves: python gerar_chaves.py verificar")
    print("="*60)