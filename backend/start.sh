#!/bin/bash

# Script de inicio rápido para el backend FastAPI

echo "🚀 Iniciando backend FastAPI..."
echo ""

# Verificar si existe .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Crear uno basado en el ejemplo."
    cp .env.example .env 2>/dev/null || echo "Por favor, crear .env con las variables de entorno."
fi

# Instalar dependencias si es necesario
if [ ! -d "venv" ]; then
    echo "📦 Creando ambiente virtual..."
    python3 -m venv venv
fi

# Activar ambiente virtual
echo "✅ Activando ambiente virtual..."
source venv/bin/activate

# Instalar/actualizar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

# Ejecutar servidor
echo ""
echo "🔥 Servidor Uvicorn iniciado en:"
echo "   http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload

