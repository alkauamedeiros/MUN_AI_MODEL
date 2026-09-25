import logging
import os
from datetime import datetime

def setup_logger():
    """Configura o logger global para gravar em arquivo e exibir no console."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    #Nome do arquivo de log baseado na data atual
    log_filename = os.path.join(log_dir, f"execucao_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    #Formato do log: [Data Hora] [Nível] [Nome da Classe/Arquivo]: Mensagem
    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(logging.DEBUG)
    
    #Configura se ainda não houver handlers registrados
    if not logger_raiz.hasHandlers():
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        #Salva tudo, incluindo DEBUG nas logs
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger_raiz.addHandler(file_handler)
        
        #Exibe apenas INFO e superior no terminal para não poluir a tela
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger_raiz.addHandler(console_handler)

    #Muda o nível de logs de algumas bibliotecas
    bibliotecas_ruidosas = [
        "httpx", "httpcore", "urllib3", "faster_whisper", 
        "ctranslate2", "onnxruntime", "asyncio", "torch"
    ]
    for lib in bibliotecas_ruidosas:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    logging.getLogger("torio").setLevel(logging.WARNING)
    logging.getLogger("torchaudio").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)

def formatar_discurso_log(text, max_chars = 150):
    """Remove quebras de linha e limita o tamanho do texto para o log."""

    texto_formatado = " ".join(text.split())

    if len(texto_formatado) > max_chars:
        return f'"{texto_formatado[:max_chars]}..." [Total: {len(texto_formatado)} chars]'
    return f'"{texto_formatado}"'