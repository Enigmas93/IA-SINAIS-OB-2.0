# Script de Deploy para Vercel
# Execute este script no PowerShell para fazer o deploy automatizado

Write-Host "🚀 Iniciando deploy na Vercel..." -ForegroundColor Green

# Verificar se o Vercel CLI está instalado
if (!(Get-Command "vercel" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Vercel CLI não encontrado. Instalando..." -ForegroundColor Red
    npm install -g vercel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao instalar Vercel CLI" -ForegroundColor Red
        exit 1
    }
}

# Verificar se está logado na Vercel
Write-Host "🔐 Verificando login na Vercel..." -ForegroundColor Yellow
vercel whoami
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Não está logado na Vercel. Execute 'vercel login' primeiro" -ForegroundColor Red
    exit 1
}

# Verificar arquivos necessários
Write-Host "📋 Verificando arquivos necessários..." -ForegroundColor Yellow

$requiredFiles = @(
    "vercel.json",
    "api/index.py",
    "app_vercel.py",
    "requirements-vercel.txt",
    ".env.production"
)

foreach ($file in $requiredFiles) {
    if (!(Test-Path $file)) {
        Write-Host "❌ Arquivo necessário não encontrado: $file" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ $file" -ForegroundColor Green
}

# Mostrar estrutura do projeto
Write-Host "\n📁 Estrutura do projeto:" -ForegroundColor Cyan
Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -notmatch '^(__pycache__|.git|node_modules|venv|env)$' } | ForEach-Object {
    Write-Host "  📂 $($_.FullName.Replace($PWD.Path, '.'))/" -ForegroundColor Blue
}

# Perguntar sobre o tipo de deploy
Write-Host "\n🎯 Escolha o tipo de deploy:" -ForegroundColor Cyan
Write-Host "1. Deploy de desenvolvimento (preview)" -ForegroundColor White
Write-Host "2. Deploy de produção" -ForegroundColor White
$choice = Read-Host "Digite sua escolha (1 ou 2)"

switch ($choice) {
    "1" {
        Write-Host "\n🔧 Fazendo deploy de desenvolvimento..." -ForegroundColor Yellow
        vercel
    }
    "2" {
        Write-Host "\n🚀 Fazendo deploy de produção..." -ForegroundColor Green
        vercel --prod
    }
    default {
        Write-Host "❌ Opção inválida. Execute o script novamente." -ForegroundColor Red
        exit 1
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "\n✅ Deploy concluído com sucesso!" -ForegroundColor Green
    Write-Host "\n📊 Para monitorar o deploy:" -ForegroundColor Cyan
    Write-Host "  • Acesse: https://vercel.com/dashboard" -ForegroundColor White
    Write-Host "  • Verifique os logs em tempo real" -ForegroundColor White
    Write-Host "  • Configure as variáveis de ambiente se necessário" -ForegroundColor White
    
    Write-Host "\n🔧 Comandos úteis:" -ForegroundColor Cyan
    Write-Host "  vercel logs <url>     - Ver logs do deploy" -ForegroundColor White
    Write-Host "  vercel env ls         - Listar variáveis de ambiente" -ForegroundColor White
    Write-Host "  vercel domains        - Gerenciar domínios" -ForegroundColor White
} else {
    Write-Host "\n❌ Erro durante o deploy. Verifique os logs acima." -ForegroundColor Red
    Write-Host "\n🔍 Dicas para resolver problemas:" -ForegroundColor Yellow
    Write-Host "  • Verifique se todas as variáveis de ambiente estão configuradas" -ForegroundColor White
    Write-Host "  • Confirme que o requirements-vercel.txt está correto" -ForegroundColor White
    Write-Host "  • Teste localmente com: python app_vercel.py" -ForegroundColor White
    exit 1
}

Write-Host "\n🎉 Deploy finalizado!" -ForegroundColor Green