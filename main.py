import os
import gspread
import telebot
import json  # <--- NOVO: Usaremos a biblioteca padrão de JSON
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pytz import timezone

# --- CONFIGURAÇÃO (via Variáveis de Ambiente) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_CREDS_JSON_STRING = os.environ.get('GOOGLE_CREDS_JSON_STRING')
SPREADSHEET_NAME = os.environ.get('SPREADSHEET_NAME')

# --- INICIALIZAÇÃO ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)
server = Flask(__name__)

# --- FUNÇÕES DO BOT ---
def conectar_planilha():
    try:
        # ALTERADO: Trocamos o perigoso 'eval()' pelo seguro 'json.loads()'
        creds_dict = json.loads(GOOGLE_CREDS_JSON_STRING)
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.for_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print(f"Erro ao conectar com a planilha: {e}")
        return None

def processar_gasto(message):
    try:
        texto_mensagem = message.text
        descricao_str, valor_str, especie_str = texto_mensagem.split(';')
        descricao = descricao_str.strip()
        especie = especie_str.strip()
        valor_limpo = valor_str.strip().replace('.', '').replace(',', '.')
        valor = float(valor_limpo)
        
        fuso_horario_brasil = timezone('America/Sao_Paulo')
        agora = datetime.now(fuso_horario_brasil)
        data_atual = agora.strftime('%d/%m/%Y')
        hora_atual = agora.strftime('%H:%M:%S')
        
        planilha = conectar_planilha()
        if planilha:
            nova_linha = [data_atual, hora_atual, descricao, valor, especie]
            planilha.append_row(nova_linha)
            valor_formatado = f'{valor:_.2f}'.replace('.', ',').replace('_', '.')
            bot.send_message(message.chat.id, f"✅ Gasto registrado!\n\n- Descrição: {descricao}\n- Valor: R$ {valor_formatado}\n- Espécie: {especie}")
        else:
            bot.send_message(message.chat.id, "❌ Desculpe, não consegui me conectar à planilha.")
    except Exception as e:
        print(f"Ocorreu um erro durante o processamento: {e}")
        bot.send_message(message.chat.id, "❌ Ocorreu um erro inesperado ao processar sua mensagem.")

# --- ROTA PARA O TELEGRAM ENVIAR AS MENSAGENS ---
@server.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    
    # ALTERADO: Adicionamos uma verificação para só processar mensagens de texto
    if update.message and update.message.text:
        processar_gasto(update.message)
        
    return "!", 200

# --- ROTA PARA O HEALTH CHECK DO RENDER ---
@server.route("/")
def health_check():
    return "App está rodando!", 200
