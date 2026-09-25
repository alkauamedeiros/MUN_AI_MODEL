import tkinter as tk
import threading
import queue
import os #Necessário para checar se o arquivo da bandeira existe
import logging

logger = logging.getLogger(__name__)

ui_queue = queue.Queue()

# Evento para sinalizar o pressionamento da barra de espaço entre threads
espaco_event = threading.Event()

def check_reset_espaco():
    """Verifica se a barra de espaço foi pressionada e reseta a sinalização."""
    if espaco_event.is_set():
        espaco_event.clear()
        return True
    return False

def _on_space_press(event):
    logger.info("Barra de espaço pressionada na janela do display.")
    espaco_event.set()


def _run_display():
    """Executa o loop da interface gráfica em uma thread separada"""

    try:
        logger.info("Inicializando janela Tkinter da interface gráfica...")

        root = tk.Tk()
        root.title("Interface do Agente")
        root.geometry("1200x800")
        root.configure(bg="white")

        #CONFIGURA A BARRA DE ESPAÇO
        root.bind("<space>", _on_space_press)
        
        status_label = tk.Label(
            root, text="Agente artificial ouvindo...", 
            font=("Arial", 32, "bold"), bg="white", fg="#2E7D32" 
        )
        status_label.pack(side=tk.TOP, pady=(40, 20))
        
        #Label da bandeira modificado para suportar imagens
        flag_label = tk.Label(
            root, 
            text="[ Aguardando ]", 
            font=("Arial", 22, "bold"), 
            bg="white", 
            fg="black"
        )
        flag_label.pack(side=tk.BOTTOM, pady=(20, 40))
        
        canvas = tk.Canvas(root, bg="white", highlightthickness=0)
        canvas.pack(side=tk.TOP, expand=True, fill="both", padx=40, pady=10)
        
        anim_data = {
            'is_scrolling': False,
            'text_id': None,
            'speed': 0.5
        }
        
        #Dicionário de cache vital para as imagens não sumirem
        image_cache = {}

        def scroll_text():
            if anim_data['is_scrolling'] and anim_data['text_id'] is not None:
                bbox = canvas.bbox(anim_data['text_id'])
                if bbox:
                    altura_limite = canvas.winfo_height() * 0.3
                    if bbox[3] > altura_limite:
                        canvas.move(anim_data['text_id'], 0, -anim_data['speed'])
            if anim_data['is_scrolling']:
                root.after(40, scroll_text)
        
        def check_queue():
            try:
                while True:
                    msg = ui_queue.get_nowait()
                    if msg['action'] == 'ouvindo':
                        logger.info("Interface gráfica alterada para o estado: OUVINDO")
                        status_label.config(text="Agente artificial ouvindo...", fg="#2E7D32")
                        flag_label.config(image='', text="[ Aguardando ]", relief="solid", width=30, height=5, bg="#EEEEEE")
                        
                        anim_data['is_scrolling'] = False
                        canvas.delete("all")
                        
                    elif msg['action'] == 'falando':
                        logger.info(f"Interface gráfica alterada para o estado: FALANDO")
                        status_label.config(text="Agente artificial falando", fg="#D32F2F")
                        
                        #LOGICA DA BANDEIRA AQUI
                        country_name = msg['country']
                        flag_path = f"../flags/{country_name}.png"
                        
                        #Checa se o arquivo de fato existe na pasta
                        if os.path.exists(flag_path):
                            #Carrega a imagem e guarda no cache
                            if country_name not in image_cache:
                                try:
                                    image_cache[country_name] = tk.PhotoImage(file=flag_path)
                                    logger.debug(f"Imagem da bandeira adicionada ao cache: '{flag_path}'")
                                except Exception as e:
                                    logger.error(f"Erro ao carregar imagem da bandeira em '{flag_path}': {e}", exc_info=True)

                            if country_name in image_cache:
                                #Remove o texto/bordas e exibe a imagem limpa
                                flag_label.config(
                                    image=image_cache[country_name], 
                                    text="", #Esconde o texto
                                    relief="flat", 
                                    bg="white",
                                    width=300, #A largura da sua imagem
                                    height=200 #A altura da sua imagem
                                )
                            else:
                                flag_label.config(
                                    image='', 
                                    text=f"[ Falha na Imagem: {country_name} ]", 
                                    relief="solid", width=30, height=5, bg="#EEEEEE"
                                )
                        else:
                            logger.warning(f"Bandeira para o país '{country_name}' não foi encontrada em '{flag_path}'. Exibindo fallback.")
                            flag_label.config(
                                image='', 
                                text=f"[ Bandeira Ausente: {country_name} ]", 
                                relief="solid", width=30, height=5, bg="#EEEEEE"
                            )
                        
                        anim_data['is_scrolling'] = False
                        canvas.delete("all")
                        
                        root.update_idletasks()
                        w = canvas.winfo_width()
                        h = canvas.winfo_height()
                        
                        start_y = h / 2
                        
                        anim_data['text_id'] = canvas.create_text(
                            w / 2, start_y, text=msg['text'],
                            font=("Arial", 28), fill="black", width=1000,
                            justify="center", anchor="n"
                        )
                        
                        anim_data['is_scrolling'] = True
                        scroll_text()
                        
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Erro inesperado no processamento da fila da interface: {e}", 
                             exc_info=True)
            
            root.after(100, check_queue)

        check_queue()
        logger.info("Loop principal da interface gráfica (Tkinter) iniciado.")
        root.mainloop()

    except Exception as e:
        logger.error(f"Falha crítica na execução da interface gráfica: {e}", 
                     exc_info=True)

def start_display_thread():
    logger.info("Iniciando thread dedicada da interface gráfica.")
    t = threading.Thread(target=_run_display, daemon=True)
    t.start()

def set_ouvindo():
    logger.debug("Sinalizador de estado 'ouvindo' enviado para a fila da interface.")
    ui_queue.put({'action': 'ouvindo'})

def set_falando(text, country):
    logger.debug(f"Sinalizador de estado 'falando' (País: '{country}') enviado para a fila da interface.")
    ui_queue.put({'action': 'falando', 'text': text, 'country': country})