import os
import gspread
import telebot
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pytz import timezone

# --- CONFIGURAÇÃO (Agora via Variáveis de Ambiente) ---
# Vamos configurar estes valores diretamente no Render, não mais no código.
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_CREDS_JSON_STRING = os.environ.get('GOOGLE_CREDS_JSON_STRING')
SPREADSHEET_NAME = os.environ.get('SPREADSHEET_NAME')

# URL do nosso serviço no Render (vamos descobrir depois de publicar)
# Exemplo: 'https://seu-bot.onrender.com'
APP_URL = os.environ.get('APP_URL')

# --- INICIALIZAÇÃO ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)
server = Flask(__name__)

# --- FUNÇÕES DO BOT (Semelhantes às que já tínhamos) ---
def conectar_planilha():
    try:
        # Converte a string JSON (da variável de ambiente) em um dicionário
        creds_dict = eval(GOOGLE_CREDS_JSON_STRING)
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.for_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print(f"Erro ao conectar com a planilha: {e}")
        return None

def processar_gasto(message):
    """Função que processa a mensagem de texto e adiciona à planilha."""
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
    except ValueError:
        bot.send_message(message.chat.id, "Formato inválido. Por favor, envie no formato: *Descrição; Valor; Espécie*")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        bot.send_message(message.chat.id, "❌ Ocorreu um erro inesperado.")

# --- WEBHOOK: A NOVA FORMA DE RECEBER MENSAGENS ---
@server.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    # Remove qualquer webhook antigo e define o novo
    bot.remove_webhook()
    bot.set_webhook(url=f'{APP_URL}/{TELEGRAM_TOKEN}')
    return "Webhook configurado!", 200

# --- INICIALIZAÇÃO DO SERVIDOR (Para o Render usar) ---
if __name__ == "__main__":
    # Esta parte é para testes locais, o Render usará um comando diferente
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))