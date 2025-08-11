# ⚙️ Configurações do Dashboard da Vercel

## 📋 O que Preencher nos Campos da Vercel

Quando você fizer o deploy na Vercel, será apresentado com alguns campos de configuração. Aqui está exatamente o que colocar em cada um:

### 🔧 Build and Output Settings

#### 1. **Build Command** 📦
```bash
# DEIXE VAZIO ou use:
pip install -r requirements-vercel.txt
```

**Explicação**: 
- Para projetos Python/Flask, geralmente não precisamos de build command
- A Vercel instala automaticamente as dependências do `requirements-vercel.txt`
- Se deixar vazio, a Vercel detecta automaticamente

#### 2. **Output Directory** 📁
```
# DEIXE VAZIO
```

**Explicação**:
- Para aplicações serverless Python, não há diretório de output
- A Vercel usa diretamente os arquivos da raiz e da pasta `api/`
- Deixe este campo vazio

#### 3. **Install Command** 📥
```bash
pip install -r requirements-vercel.txt
```

**Explicação**:
- Este comando instala as dependências Python
- Usa o arquivo `requirements-vercel.txt` que criamos (otimizado para Vercel)
- A Vercel executará este comando automaticamente

---

## 🚀 Configuração Completa Passo a Passo

### Passo 1: Conectar Repositório
1. Acesse [vercel.com](https://vercel.com)
2. Clique em "New Project"
3. Conecte seu repositório Git (GitHub, GitLab, etc.)
4. Ou faça upload manual dos arquivos

### Passo 2: Configurar Build Settings

**Framework Preset**: `Other`

**Build and Output Settings**:
- ✅ **Build Command**: `pip install -r requirements-vercel.txt` (ou deixe vazio)
- ✅ **Output Directory**: (deixe vazio)
- ✅ **Install Command**: `pip install -r requirements-vercel.txt`

### Passo 3: Environment Variables (IMPORTANTE! 🔑)

Clique em "Environment Variables" e adicione:

```
SECRET_KEY=3f69a98ab89b8982e4f3f0618984fefc1cbe70d72535e3e5b1c5cbcf3ec3be09
JWT_SECRET_KEY=678e787fc1ba36f076008dc9c9cfb87e9a6b8528c3b63db75dabed331e92a16dc18c23bc336f5976fadff6814a9a6559d5c2ad5b51ac9e6ebcb87c17d13daa03
FLASK_ENV=production
FLASK_DEBUG=False
JWT_ACCESS_TOKEN_EXPIRES=24
LOG_LEVEL=INFO
CORS_ORIGINS=*
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
DATABASE_URL=sqlite:///trading_bot.db
```

**Para cada variável**:
- **Environment**: Selecione `Production`, `Preview`, e `Development`
- **Value**: Cole o valor exato

### Passo 4: Deploy
1. Clique em "Deploy"
2. Aguarde o build completar
3. Acesse a URL gerada

---

## 📁 Estrutura de Arquivos Necessária

Certifique-se de que estes arquivos estão no seu projeto:

```
✅ vercel.json                 # Configuração da Vercel
✅ api/index.py               # Ponto de entrada
✅ app_vercel.py              # App Flask otimizada
✅ requirements-vercel.txt     # Dependências otimizadas
✅ static/                    # Arquivos CSS, JS, imagens
✅ templates/                 # Templates HTML
✅ services/                  # Serviços da aplicação
✅ models.py                  # Modelos do banco
✅ routes.py                  # Rotas da API
```

---

## 🔍 Troubleshooting - Problemas Comuns

### ❌ Erro: "Build failed"
**Solução**:
- Verifique se `requirements-vercel.txt` existe
- Confirme que não há dependências problemáticas
- Use: `pip install -r requirements-vercel.txt` como Install Command

### ❌ Erro: "Function timeout"
**Solução**:
- Verifique se `vercel.json` tem `"maxDuration": 30`
- Otimize código para ser mais rápido
- Remova processamentos pesados

### ❌ Erro: "Module not found"
**Solução**:
- Adicione a dependência em `requirements-vercel.txt`
- Verifique imports no `app_vercel.py`
- Confirme estrutura de pastas

### ❌ Erro: "Environment variable not set"
**Solução**:
- Adicione todas as variáveis no dashboard
- Verifique nomes exatos (case-sensitive)
- Redeploy após adicionar variáveis

### ✅ Erro Corrigido: "404: NOT_FOUND"

**Problema:** A aplicação estava tentando importar dependências complexas que causavam falhas no ambiente serverless.

**Solução Aplicada:**
1. **Simplificação do `api/index.py`:** Removidas dependências complexas e criada versão standalone
2. **Configuração otimizada do `vercel.json`:** Simplificada para configuração mínima funcional
3. **Template HTML inline:** Removida dependência de arquivos de template externos

### ❌ Erro: "A propriedade 'functions' não pode ser usada em conjunto com a propriedade 'builds'"
**Solução**:
- Este erro ocorre quando há conflito no `vercel.json`
- Remova a seção `"functions"` do arquivo `vercel.json`
- Use apenas `"builds"` e `"routes"`

### ✅ Configuração Final Funcional

O arquivo `vercel.json` otimizado:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/api/index.py"
    }
  ],
  "env": {
    "FLASK_ENV": "production"
  }
}
```

---

## 🎯 Resumo Rápido

### No Dashboard da Vercel:

1. **Framework**: Other
2. **Build Command**: `pip install -r requirements-vercel.txt` (ou vazio)
3. **Output Directory**: (vazio)
4. **Install Command**: `pip install -r requirements-vercel.txt`
5. **Environment Variables**: Adicione todas as chaves do arquivo `.env.local`

### Arquivos Importantes:
- ✅ `vercel.json` - Configuração
- ✅ `api/index.py` - Entrada
- ✅ `app_vercel.py` - App otimizada
- ✅ `requirements-vercel.txt` - Dependências

### Comandos Úteis:
```bash
# Deploy manual
vercel --prod

# Ver logs
vercel logs [url]

# Listar variáveis
vercel env ls
```

---

## 🔗 Links Úteis

- [Dashboard Vercel](https://vercel.com/dashboard)
- [Documentação Python](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)

---

**💡 Dica**: Depois de configurar, teste localmente com `python app_vercel.py` antes de fazer deploy!