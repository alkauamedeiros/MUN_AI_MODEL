import sqlite3
from ollama_config import ollama_client
import logging
import time

logger = logging.getLogger(__name__)


class DataMatrix:
    def __init__(
        self, 
        db_path: str = "../data_matrix.db",
        overwrite: bool = False,
        table_name: str = "discourse",
        col_row: str = "autor",
        col_column: str = "receiver",
        col_data: str = "text_data",
        sep_instructions: str = "../instrucoes/sep_instructions.txt",
        correct_instructions: str = "../instrucoes/correct_instructions.txt",
        activation_instructions: str = "../instrucoes/ai_activation.txt"
    ):
        self.db_path = db_path
        self.table_name = table_name
        self.col_row = col_row
        self.col_column = col_column
        self.col_data = col_data
        
        self.conn = sqlite3.connect(self.db_path)

        if(overwrite):
            with self.conn:
                self.conn.execute(f"DROP TABLE IF EXISTS {self.table_name}")

        self._create_table_and_indices()

        #AGENT VARIABLES#
        self.sep_instructions = sep_instructions
        self.correct_instructions = correct_instructions
        self.activation_instructions = activation_instructions
        self.last_row = ''
        self.last_column = ''

    def _create_table_and_indices(self) -> None:
        index_name = f"idx_{self.table_name}_{self.col_row}_{self.col_column}"
        
        with self.conn:
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {self.col_row} TEXT NOT NULL,
                    {self.col_column} TEXT NOT NULL,
                    {self.col_data} TEXT NOT NULL
                )
            """)
            self.conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {self.table_name} ({self.col_row}, {self.col_column})
            """)

    def insert(self, autor: str, receiver: str, text_data: str) -> None:
        with self.conn:
            self.conn.execute(
                f"INSERT INTO {self.table_name} ({self.col_row}, {self.col_column}, {self.col_data}) VALUES (?, ?, ?)",
                (autor, receiver, text_data)
            )

    def search_cell(self, autor: str, receiver: str, separator: str = "\n\n") -> str:
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT group_concat({self.col_data}, ?) FROM {self.table_name} WHERE {self.col_row} = ? AND {self.col_column} = ?",
            (separator, autor, receiver)
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else ""

    def close_matrix(self) -> None:
        self.conn.close()
    
    def agent_insertion(self, text):
        """Realiza a inserção do texto na matriz de dados usando uma call do agente qwen3.5:9b"""

        logger.info(f"Iniciando processo de inserção de dados na matriz de dados.")
        tempo_inicio = time.perf_counter()

        try:
            #Lê as instruções
            sep_instructions = ''
            with open(self.sep_instructions, "r", encoding="utf-8") as op:
                sep_instructions = op.read()

            correct_instructions = ''
            with open(self.correct_instructions, "r", encoding="utf-8") as op:
                correct_instructions = op.read()
            
            #Faz a call para o agente de IA

            tempo_inicio_rag = time.perf_counter()
            
            stream1 = ollama_client.chat(
                model = 'qwen3.5:9b',
                messages=[
                    {
                        'role' : 'system',
                        'content' :  sep_instructions,
                    },

                    {
                        'role' : 'user',
                        'content' : f"Trecho a ser classificado: '{text}'\nRetorne no formato adequado.",
                    },
                ],
                think = False,
                stream = False,
                options={'temperature' : 0.1,}
            )

            tempo_rag = time.perf_counter() - tempo_inicio_rag
            logger.debug(f"O RAG realizou a instrução em {tempo_rag:.2f}s.")
            
            #Decisão do modelo
            decision = stream1['message']['content']

            logger.debug(f'A decisão do RAG foi: "{" ".join(decision.split())}"')


            #Correção de erros de ortografia pelo mesmo modelo rodado novamente

            tempo_inicio_correct = time.perf_counter()

            stream2 = ollama_client.chat(
                model = 'qwen3.5:9b',
                messages=[
                    {
                        'role' : 'system',
                        f'content' :  correct_instructions,
                    },

                    {
                        'role' : 'user',
                        'content' : f"Trecho a ser corrigido: '{decision}'\nRetorne no formato adequado. Corrija erros de ortografia dos nomes dos países.",
                    },
                ],
                think = False,
                stream = False,
                options={'temperature' : 0.1,}
            )

            tempo_correct = time.perf_counter() - tempo_inicio_correct

            logger.info(f"O corretor realizou a instrução em {tempo_correct:.2f}s.")
            
            correct_decision = stream2['message']['content']

            logger.info(f'O corretor deu essa resposta: "{" ".join(correct_decision.split())}"')

            #Começa as inserções:
            insertions = correct_decision.split('\n')
            for line in insertions:
                #Divide entre quem falou e sobre quem foi falado
                divisor = line.split(';')

                #Pega quem falou
                autor = str(divisor[0])

                if(autor != '' and autor.upper() != 'OUTROS'):
                    #INSERE EM SI PRÓPRIO
                    self.insert(autor, autor, text)
                    logger.info(f"Inserção na matriz na posição ({autor},{autor}).")

                    if(len(divisor) > 1):
                        #Subdivide em cada um sobre o qual foi falado
                        sub_divisor = divisor[1].split(' ')
                        for receiver in sub_divisor:
                            if(receiver != '' and receiver.upper() != 'OUTROS' and receiver.upper() != autor.upper()):
                                #Insere na matriz de forma simétrica.
                                self.insert(autor, receiver, text)
                                self.insert(receiver, autor, text)
                                logger.info(f"Inserção na matriz na posição ({autor},{receiver}).")

            tempo_decorrido = time.perf_counter() - tempo_inicio
            logger.info(f"Inserção do discurso na matriz de dados concluída após {tempo_decorrido:.2f}s.")

        except Exception as e:
            tempo_decorrido = time.perf_counter() - tempo_inicio
            logger.error(
                f"Falha na inserção do discurso após {tempo_decorrido:.2f}s: {e}",
                exc_info=True
            )

    def ai_activation(self, text):
        """Retorna um texto que indica a ativação ou não da IA"""

        logger.info("Iniciando processo de identificação da ativação do agente.")
        tempo_inicio = time.perf_counter()

        try:
            activation_instructions = ''
            with open(self.activation_instructions, "r", encoding="utf-8") as op:
                activation_instructions = op.read()

            #Faz a call para o agente de IA
            stream = ollama_client.chat(
                model = 'qwen3.5:9b',
                messages=[
                    {
                        'role' : 'system',
                        'content' :  activation_instructions,
                    },

                    {
                        'role' : 'user',
                        'content' : f"Trecho para detectar a ativação: '{text}'\nRetorne no formato adequado.",
                    },
                ],
                think = False,
                stream = False,
                options={'temperature' : 0.1,}
            )

            decision = stream['message']['content']

            tempo_decorrido = time.perf_counter() - tempo_inicio
            logger.info(f'A resposta (decisão) da IA foi gerada em {tempo_decorrido:.2f}s | A decisão foi: "{decision}"')

            if("NO" in decision.upper() or "ACTIVATION" in decision.upper()):
                logger.info("Não foi detectada uma ativação do Agente.")
                return None
            
            to_ask = decision.split(' ')
            if(len(to_ask) == 3):
                logger.info("Foi detectada uma ativação do Agente.")
                return (to_ask[1],to_ask[2])
            else:
                logger.warning(f'A resposta de ativação retornou em um formato inesperado: "{decision}"')
        except Exception as e:
            tempo_decorrido = time.perf_counter() - tempo_inicio
            logger.error(f"Falha na detecção do Agente após {tempo_decorrido}s: {e}",
                         exc_info=True)