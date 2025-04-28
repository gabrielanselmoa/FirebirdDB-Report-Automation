import fdb
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações do Banco de Dados ---
# Ajuste o DSN conforme necessário
DATABASE_PATH = os.getenv("DATABASE_PATH")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

# --- Configurações para a Geração de Dados ---
num_inserts_por_tabela = 50

# Faixa de datas para pagamentos aleatórios
data_inicio_pagamentos = datetime(2022, 1, 1)
data_fim_pagamentos = datetime(2024, 12, 31)
delta_tempo_pagamentos = data_fim_pagamentos - data_inicio_pagamentos
total_dias_no_range_pagamentos = delta_tempo_pagamentos.days


# --- Conexão com o Banco Firebird ---
con = None
cur = None

try:
    con = fdb.connect(dsn=DATABASE_PATH, user=USER, password=PASSWORD)
    cur = con.cursor()
    print("Conectado ao banco de dados Firebird!")

    # --- Função para Gerar Dados e Inserir ---
    def gerar_e_inserir_dados():
        # --- Limpar Tabelas (Ordem Importa Devido a Chaves Estrangeiras) ---
        tabelas_para_limpar = [
            "PAGAMENTOS",
            "CONTRATOS",
            "CLIENTES",
            "ENDERECOS",
            "PRODUTOS",
            "CATEGORIAS",
            "FUNCIONARIOS"
        ]

        print("\nIniciando limpeza das tabelas...")
        for tabela in tabelas_para_limpar:
            try:
                cur.execute(f"DELETE FROM {tabela}")
                print(f"Dados excluídos da tabela {tabela}.")
            except fdb.DatabaseError as e:
                print(f"Erro ao excluir dados da tabela {tabela}: {e}")
                print("A exclusão pode falhar se houver dependências não listadas ou dados que não puderam ser excluídos.")
                # Dependendo da severidade, você pode querer dar rollback e parar aqui
                # con.rollback()
                # return # Sai da função

        # Confirmar exclusões antes de inserir
        con.commit()
        print("Limpeza de tabelas concluída e confirmada.")

        # --- Inserir Novamente (50 registros por tabela) ---
        print(f"\nIniciando inserção de {num_inserts_por_tabela} registros por tabela...")

        # CATEGORIAS
        categorias_para_inserir = [(i, f"Categoria {i}") for i in range(1, num_inserts_por_tabela + 1)]
        cur.executemany("INSERT INTO CATEGORIAS (ID, NOME) VALUES (?, ?)", categorias_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em CATEGORIAS.")

        # ENDERECOS
        enderecos_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
            enderecos_para_inserir.append((i, f"Rua {i}", str(i), f"Bairro {i}", f"Cidade {i}", "UF", f"CEP-{i:03d}"))
        cur.executemany("INSERT INTO ENDERECOS (ID, RUA, NUMERO, BAIRRO, CIDADE, ESTADO, CEP) VALUES (?, ?, ?, ?, ?, ?, ?)", enderecos_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em ENDERECOS.")

        # CLIENTES
        clientes_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
            # ENDERECO_ID deve estar dentro do range de endereços inseridos (1 a 50)
            endereco_id_cliente = random.randint(1, num_inserts_por_tabela)
            clientes_para_inserir.append((i, f"Cliente {i}", f"cliente{i}@email.com", f"({random.randint(10, 99)}) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}", "1990-01-01", endereco_id_cliente))
        cur.executemany("INSERT INTO CLIENTES (ID, NOME, EMAIL, TELEFONE, DATA_NASCIMENTO, ENDERECO_ID) VALUES (?, ?, ?, ?, ?, ?)", clientes_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em CLIENTES.")

        # PRODUTOS
        produtos_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
             # CATEGORIA_ID deve estar dentro do range de categorias inseridas (1 a 50)
            categoria_id_produto = random.randint(1, num_inserts_por_tabela)
            produtos_para_inserir.append((i, f"Produto {i}", categoria_id_produto, round(random.uniform(50.00, 500.00), 2), random.randint(5, 100)))
        cur.executemany("INSERT INTO PRODUTOS (ID, NOME, CATEGORIA_ID, PRECO_DIARIA, QUANTIDADE_DISPONIVEL) VALUES (?, ?, ?, ?, ?)", produtos_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em PRODUTOS.")

        # FUNCIONARIOS
        funcionarios_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
            cargos = ["Gerente", "Analista", "Suporte", "Vendedor", "Estagiário"]
            funcionarios_para_inserir.append((i, f"Funcionario {i}", random.choice(cargos), round(random.uniform(2000.00, 10000.00), 2), datetime.now() - timedelta(days=random.randint(365, 1825)))) # Datas de admissão nos últimos 1-5 anos
        cur.executemany("INSERT INTO FUNCIONARIOS (ID, NOME, CARGO, SALARIO, DATA_ADMISSAO) VALUES (?, ?, ?, ?, ?)", funcionarios_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em FUNCIONARIOS.")


        # CONTRATOS
        contratos_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
            # CLIENTE_ID e PRODUTO_ID devem estar dentro do range inserido (1 a 50)
            cliente_id_contrato = random.randint(1, num_inserts_por_tabela)
            produto_id_contrato = random.randint(1, num_inserts_por_tabela)
            data_inicio_contrato = datetime(2022, 1, 1) + timedelta(days=random.randint(0, 730)) # Datas de início nos últimos 2 anos
            data_fim_contrato = data_inicio_contrato + timedelta(days=random.randint(30, 365)) # Contratos duram 1-12 meses
            status_contrato = random.choice(["ativo", "inativo", "pendente", "cancelado"])
            contratos_para_inserir.append((i, cliente_id_contrato, produto_id_contrato, data_inicio_contrato, data_fim_contrato, status_contrato))
        cur.executemany("INSERT INTO CONTRATOS (ID, CLIENTE_ID, PRODUTO_ID, DATA_INICIO, DATA_FIM, STATUS) VALUES (?, ?, ?, ?, ?, ?)", contratos_para_inserir)
        print(f"{num_inserts_por_tabela} registros inseridos em CONTRATOS.")


        # PAGAMENTOS
        pagamentos_para_inserir = []
        for i in range(1, num_inserts_por_tabela + 1):
            # CONTRATO_ID deve estar dentro do range de contratos inseridos (1 a 50)
            contrato_id_pagamento = random.randint(1, num_inserts_por_tabela)
            valor_pago = round(random.uniform(100.00, 1000.00), 2)

            # Gerar data de pagamento aleatória dentro do range (meses e anos diferentes)
            dias_aleatorios = random.randint(0, total_dias_no_range_pagamentos)
            data_pagamento = data_inicio_pagamentos + timedelta(days=dias_aleatorios)

            pagamentos_para_inserir.append((i, contrato_id_pagamento, valor_pago, data_pagamento))

        insert_query_pagamentos = "INSERT INTO PAGAMENTOS (ID, CONTRATO_ID, VALOR_PAGO, DATA_PAGAMENTO) VALUES (?, ?, ?, ?)"
        cur.executemany(insert_query_pagamentos, pagamentos_para_inserir)
        print(f"{num_inserts_por_tabela} novos registros inseridos em PAGAMENTOS com datas variadas.")


        # --- Confirmar Todas as Alterações ---
        con.commit()
        print("\nTodas as inserções concluídas e confirmadas!")

    # --- Executar a Geração e Inserção ---
    gerar_e_inserir_dados()

except fdb.DatabaseError as e:
    print(f"\nErro no Banco de Dados: {e}")
    if con:
        con.rollback() # Desfaz qualquer alteração pendente em caso de erro
except Exception as e:
    print(f"\nOcorreu um erro inesperado: {e}")

finally:
    # --- Fechar a Conexão ---
    if cur is not None:
        cur.close()
    if con is not None:
        con.close()
    print("Conexão com o banco de dados fechada.")