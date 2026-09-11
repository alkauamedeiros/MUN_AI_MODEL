import sqlite3
from ollama_config import ollama_client

class DataMatrix:
    def __init__(
        self, 
        db_path: str = "data_matrix.db",
        overwrite: bool = False,
        table_name: str = "discourse",
        col_row: str = "autor",
        col_column: str = "receiver",
        col_data: str = "text_data",
        sep_instructions: str = "sep_instructions.txt",
        correct_instructions: str = "correct_instructions.txt"
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

        #Lê as instruções
        sep_instructions = ''
        with open(self.sep_instructions, "r", encoding="utf-8") as op:
            sep_instructions = op.read()

        correct_instructions = ''
        with open(self.correct_instructions, "r", encoding="utf-8") as op:
            correct_instructions = op.read()
        
        #Faz a call para o agente de IA
        stream1 = ollama_client.chat(
            model = 'qwen3.5:9b',
            messages=[
                {
                    'role' : 'system',
                    'content' :  sep_instructions,
                },

                {
                    'role' : 'user',
                    'content' : f"Trecho a ser classificado: '{text}'\nRetorne no formato adequado. Lembre-se de apenas adicionar '!START' se houver a palavra-chave 'agente artificial' no texto. Palavras como 'inteligência artificial' NUNCA devem ativar o !START se não houver a palavra-chave 'agente artificial'",
                },
            ],
            think = False,
            stream = False,
            options={'temperature' : 0.1,}
        )

        #Decisão do modelo
        decision = stream1['message']['content']

        #print(decision)

        #Correção de erros de ortografia pelo mesmo modelo rodado novamente
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

        correct_decision = stream2['message']['content']
        print(correct_decision)

        #Começa as inserções:
        insertions = correct_decision.split('\n')
        try:
            for line in insertions:
                #Se for um comando para a IA
                if('!' in line):
                    to_ask = line.split(' ')
                    print("A IA IRÁ FAZER UMA PERGUNTA")
                    print(f"LINHA: {line}")
                    return (to_ask[1],to_ask[2])
                else:
                    #Divide entre quem falou e sobre quem foi falado
                    divisor = line.split(';')

                    #Pega quem falou
                    autor = str(divisor[0])

                    if(autor != '' and autor.upper() != 'OUTROS'):
                        #INSERE EM SI PRÓPRIO
                        self.insert(autor, autor, text)
                        print(f"({autor},{autor})")

                        #Subdivide em cada um sobre o qual foi falado
                        sub_divisor = divisor[1].split(' ')
                        for receiver in sub_divisor:
                            if(receiver != '' and receiver.upper() != 'OUTROS' and receiver.upper() != autor.upper()):
                                #Insere na matriz de forma simétrica.
                                self.insert(autor, receiver, text)
                                self.insert(receiver, autor, text)
                                print(f"({autor},{receiver})")
        except:
            print('\n')
            print("ERRO NA INSERÇÃO")
            print('\n')
            return None

        return None


# --- Exemplo de Uso ---
if __name__ == "__main__":
    db = DataMatrix()

    db.insert("Alice", "Bob", "Primeiro texto falado por Alice sobre Bob.")
    db.insert("Alice", "Bob", "Segundo texto falado por Alice sobre Bob.")

    texto_celula = db.search_cell("Alice", "Bob")
    print(texto_celula)

    db.close_matrix()