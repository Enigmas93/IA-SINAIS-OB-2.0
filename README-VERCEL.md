# Deploy na Vercel - Guia Completo

## 📋 Estrutura de Arquivos para Deploy

Este projeto foi otimizado para deploy na Vercel com os seguintes arquivos específicos:

### Arquivos Principais
- `vercel.json` - Configuração do Vercel
- `api/index.py` - Ponto de entrada para serverless
- `app_vercel.py` - Aplicação Flask otimizada para serverless
- `requirements-vercel.txt` - Dependências otimizadas
- `.env.production` - Variáveis de ambiente para produção
- `.vercelignore` - Arquivos a serem ignorados no deploy

## 🚀 Passos para Deploy

### 1. Preparação do Projeto

1. **Instale o Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Faça login na Vercel**:
   ```bash
   vercel login
   ```

### 2. Configuração das Variáveis de Ambiente

No dashboard da Vercel, configure as seguintes variáveis:

```
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=seu-secret-key-super-seguro
JWT_SECRET_KEY=seu-jwt-secret-key-super-seguro
DATABASE_URL=sua-url-do-banco-de-dados
JWT_ACCESS_TOKEN_EXPIRES=24
LOG_LEVEL=INFO
CORS_ORIGINS=*
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### 3. Deploy

1. **Deploy inicial**:
   ```bash
   vercel
   ```

2. **Deploy para produção**:
   ```bash
   vercel --prod
   ```

## 📁 Estrutura de Arquivos Detalhada

```
project/
├── api/
│   └── index.py              # Ponto de entrada serverless
├── static/                   # Arquivos estáticos (CSS, JS, imagens)
├── templates/                # Templates HTML
├── services/                 # Serviços da aplicação
├── models/                   # Modelos do banco de dados
├── routes/                   # Rotas da API
├── app_vercel.py            # App Flask otimizada
├── vercel.json              # Configuração Vercel
├── requirements-vercel.txt   # Dependências otimizadas
├── .env.production          # Variáveis de ambiente
├── .vercelignore           # Arquivos ignorados
└── README-VERCEL.md        # Este arquivo
```

## ⚙️ Configurações Específicas

### vercel.json
- Configura o build para usar `@vercel/python`
- Define rotas para arquivos estáticos e API
- Configura timeout de 30 segundos

### app_vercel.py
- Versão otimizada do app.py para serverless
- Remove funcionalidades que não funcionam em serverless (APScheduler, SocketIO)
- Inclui fallbacks para importações que podem falhar

### requirements-vercel.txt
- Dependências otimizadas para Vercel
- Remove bibliotecas pesadas que podem causar problemas
- Mantém apenas o essencial para funcionamento

## 🔧 Limitações do Serverless

O ambiente serverless da Vercel tem algumas limitações:

1. **Sem estado persistente**: Cada requisição é isolada
2. **Timeout**: Máximo de 30 segundos por requisição
3. **Sem processos em background**: APScheduler não funciona
4. **Sem WebSockets persistentes**: SocketIO limitado
5. **Tamanho do bundle**: Limitado a 50MB

## 🗄️ Banco de Dados

Para produção, recomenda-se usar:
- **PostgreSQL**: Heroku Postgres, Supabase, ou Neon
- **MySQL**: PlanetScale ou Railway
- **SQLite**: Apenas para testes (não persistente)

Exemplo de DATABASE_URL:
```
postgresql://username:password@host:port/database
```

## 🔍 Troubleshooting

### Erro de Import
- Verifique se todas as dependências estão em `requirements-vercel.txt`
- Confirme que os caminhos de import estão corretos

### Timeout
- Otimize consultas ao banco de dados
- Reduza processamento pesado
- Use cache quando possível

### Erro 500
- Verifique os logs na Vercel dashboard
- Confirme variáveis de ambiente
- Teste localmente com `app_vercel.py`

## 📊 Monitoramento

- Use o dashboard da Vercel para monitorar:
  - Logs de função
  - Métricas de performance
  - Uso de recursos
  - Erros e exceções

## 🔄 Atualizações

Para atualizar o deploy:
```bash
vercel --prod
```

Ou configure deploy automático conectando o repositório Git à Vercel.

## 📞 Suporte

Em caso de problemas:
1. Verifique os logs na Vercel dashboard
2. Teste localmente com `python app_vercel.py`
3. Consulte a documentação da Vercel
4. Verifique as limitações do plano gratuito