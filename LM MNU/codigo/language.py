import logging
import logger_config as log_c
import time
from ollama_config import ollama_client

logger = logging.getLogger(__name__)

def get_response(matrix, autor, receiver, user_input):
    """Gera a resposta usando o modelo 'Qwen' em uma base de dados (matriz)"""

    logger.info(f"Iniciando geração de discurso para autor='{autor}' -> receiver='{receiver}'.")
    tempo_inicio = time.perf_counter()

    try:
        question_context = ""
        try:
            with open("../instrucoes/question_context.txt", 'r', encoding="utf-8") as op:
                question_context = op.read()
        except Exception as e:
            logger.error(f"Erro crítico ao ler instruções de contexto em '../instrucoes/question_context.txt': {e}")
            return None

        
        country_context = ""
        try:
            with open(f"../contextos/{autor}_CONTEXT.txt", 'r', encoding="utf-8") as op:
                country_context = op.read()
                question_context+= country_context
        except FileNotFoundError:
            logger.warning(f"O contexto do país '{autor}' não foi encontrado. Prosseguindo sem ele.")
        except Exception as e:
            logger.warning(f"Falha ao carregar contexto do país '{autor}': {e}. Prosseguindo sem ele.")

        question_context+= matrix.search_cell(autor, autor)
        question_context+= matrix.search_cell(autor, receiver)
        question_context+= '\n\nFalas do debate:\n'+matrix.search_cell(receiver, autor)
        question_context+= '\n\nLembre-se de obedecer à formatação adequada, não usando aspas ou asteriscos. Se apresente, desenvolva sua pergunta com base nos contextos fornecidos, e faça a pergunta. Sua resposta deve ser comparável a uma fala de 1 minuto ou mais.'


        logger.info("Enviando a requisição de geração de discurso para o modelo Qwen")

        stream = ollama_client.chat(
            model = 'qwen3.5:9b',
            messages=[
                {
                    'role' : 'system',
                    'content' :  question_context,
                },

                {
                    'role' : 'user',
                    'content' : user_input,
                },
            ],
            options={'temperature' : 0.5},

            think = False,
            stream = False
        )

        tempo_decorrido = time.perf_counter() - tempo_inicio

        resposta = stream['message']['content']
        
        resposta_formatada = log_c.formatar_discurso_log(resposta)

        logger.info(f"Discurso gerado em {tempo_decorrido:.2f}s | Texto: {resposta_formatada}...")

        logger.debug(f"Discurso completo gerado: {resposta}")

        return resposta
    
    except Exception as e:
         tempo_total = time.perf_counter() - tempo_inicio
         logger.error(f"Falha ao gerar resposta para '{autor}' após {tempo_total:.2f}s: {e}",
            exc_info=True)
         return None
