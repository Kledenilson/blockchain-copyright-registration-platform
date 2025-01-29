from flask import Flask, request, jsonify
from flask_cors import CORS
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bitcoin.rpc import RawProxy
import os, time, random, sqlite3
from decimal import Decimal
from threading import Thread

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações de rede e RPC
RPC_USER = os.getenv('RPC_USER', 'myuser')
RPC_PASSWORD = os.getenv('RPC_PASSWORD', 'mypassword')
RPC_HOST = os.getenv('RPC_HOST', 'bitcoin-core')
RPC_PORT = int(os.getenv('RPC_PORT', 18443))
NETWORK = os.getenv('NETWORK', 'regtest')  # Alterna entre regtest e testnet

# Inicialização do cliente RPC
def get_rpc_connection(wallet_name=None):
    url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    if wallet_name:
        url += f"/wallet/{wallet_name}"
    return AuthServiceProxy(url)

rpc = get_rpc_connection();

# Diretório base para armazenar o banco de dados e uploads
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "transactions.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# Garante que as pastas existem
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Conexão SQLite persistente
def get_db_connection():
    return sqlite3.connect(DB_PATH)

# Banco de Dados SQLite
def init_db():
    conn = sqlite3.connect("data/transactions.db")
    cursor = conn.cursor()

    # Criação da tabela de transações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_address TEXT,
            hash TEXT,
            txid TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'doc', 'docx',  # Documentos
    'jpg', 'jpeg', 'png', 'gif',  # Imagens
    'mp3', 'wav', 'aac', 'ogg'    # Áudios
}

def allowed_file(filename):
    """Valida se a extensão do arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/block/count', methods=['GET'])
def get_block_count():
    try:
        rpc = get_rpc_connection()
        block_count = rpc.getblockcount()
        return jsonify({"status": "success", "message": "Block count retrieved successfully!", "block_count": block_count})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    
@app.route('/api/block/<int:block_number>', methods=['GET'])
def get_block_by_number(block_number):
    try:
        rpc = get_rpc_connection()
        block_hash = rpc.getblockhash(block_number)
        block = rpc.getblock(block_hash)
        return jsonify({"status": "success", "message": "Block retrieved successfully!", "block": block})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    
# Funções utilitárias
def ensure_wallet_exists(wallet_name="platform_wallet"):
    """Garante que uma carteira exista no nó Bitcoin Core."""
    try:
        rpc = get_rpc_connection()
        wallets = rpc.listwallets()

        if wallet_name in wallets:
            print(f"A carteira '{wallet_name}' já está carregada.")
        else:
            print(f"Criando ou carregando a carteira '{wallet_name}'...")
            try:
                rpc.createwallet(wallet_name)
                print(f"Carteira '{wallet_name}' criada com sucesso.")
            except JSONRPCException as e:
                if "Wallet file verification failed" in str(e):
                    print(f"Erro ao criar carteira: {e}. Tentando carregar...")
                    rpc.loadwallet(wallet_name)
                else:
                    raise
    except Exception as e:
        print(f"Erro ao verificar ou criar carteira: {e}")
        raise
def monitor_transactions():
    """Monitora transações no blockchain e atualiza o status no banco de dados."""
    rpc = get_rpc_connection()
    while True:
        time.sleep(10)  # Intervalo entre verificações
        try:
            conn = sqlite3.connect("transactions.db")
            cursor = conn.cursor()

            # Busca transações pendentes no banco
            cursor.execute("SELECT id, txid FROM transactions WHERE status = 'pending'")
            pending_transactions = cursor.fetchall()

            for tx_id, txid in pending_transactions:
                transaction = rpc.gettransaction(txid)
                confirmations = transaction.get("confirmations", 0)

                if confirmations >= 1:
                    # Atualiza o status para confirmado
                    cursor.execute("UPDATE transactions SET status = 'confirmed' WHERE id = ?", (tx_id,))
                    conn.commit()

            conn.close()
        except Exception as e:
            print(f"Erro ao monitorar transações: {e}")


def create_random_wallet(prefix="copyright_plat_"):
    """Cria uma nova carteira com um prefixo aleatório."""
    random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    wallet_name = f"{prefix}{random_suffix}"
    rpc = get_rpc_connection()
    rpc.createwallet(wallet_name)
    time.sleep(0.5)
    return wallet_name

def mine_blocks(address, num_blocks=21):
    """Gera blocos para o endereço fornecido."""
    rpc = get_rpc_connection()
    return rpc.generatetoaddress(num_blocks, address)

def initialize_wallet():
    """Inicializa a carteira padrão e gera blocos iniciais se necessário."""
    print("Verificando ou criando uma nova carteira...")
    ensure_wallet_exists()

    rpc = get_rpc_connection("platform_wallet")
    address = rpc.getnewaddress()
    print(f"Endereço gerado pelo nó (regtest): {address}")

    if rpc.getblockchaininfo()["chain"] == "regtest":
        print("Rede regtest detectada. Gerando blocos para ativação...")
        block_hashes = rpc.generatetoaddress(101, address)
        print(f"Blocos gerados: {len(block_hashes)}")
        print(f"Primeiro bloco: {block_hashes[0]}")

    return {
        'address': address
    }
    
@app.route('/api/transaction/upload', methods=['POST'])
def upload_transaction():
    """
    Recebe o upload do cliente e registra o hash no banco.
    """
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "error", "message": "Arquivo não enviado."}), 400

        data = request.form.get('data')
        if not data:
            return jsonify({"status": "error", "message": "Hash do arquivo é obrigatório."}), 400

        # Valida o hash
        try:
            bytes.fromhex(data)
        except ValueError:
            return jsonify({"status": "error", "message": "Hash inválido."}), 400

        # Salva o arquivo
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        # Gera endereço para pagamento
        wallet_name = "platform_wallet"
        rpc = get_rpc_connection(wallet_name)
        address = rpc.getnewaddress()

        # Salva no banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (client_address, hash, status) VALUES (?, ?, ?)",
            (address, data, "pending")
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Upload recebido. Aguarde confirmação de pagamento.",
            "address": address,
            "file_path": file_path  # Retorna o caminho do arquivo salvo
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro inesperado: {str(e)}"}), 500


@app.route('/api/transaction/confirm/<string:txid>', methods=['GET'])
def confirm_transaction(txid):
    """
    Verifica o status de uma transação específica.
    """
    try:
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM transactions WHERE txid = ?", (txid,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return jsonify({
                "status": "success",
                "message": "Status da transação recuperado com sucesso.",
                "txid": txid,
                "transaction_status": result[0]
            })
        else:
            return jsonify({"status": "error", "message": "Transação não encontrada."}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro inesperado: {str(e)}"}), 500


@app.route('/api/transaction/opreturn', methods=['POST'])
def create_opreturn_transaction():
    """
    Inicia o processo de criação de uma transação OP_RETURN retornando o endereço de pagamento.
    """
    try:
        # Verifica se o JSON com o hash foi enviado
        data = request.form.get('data')
        if not data:
            return jsonify({
                "status": "error",
                "message": "O campo 'data' com o hash do arquivo é obrigatório!"
            }), 400

        # Valida o hash (deve ser uma string hexadecimal)
        try:
            bytes.fromhex(data)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "O campo 'data' deve ser um hash hexadecimal válido!"
            }), 400

        # Valida o tamanho do hash para o OP_RETURN (máximo de 80 bytes)
        if len(data) > 160:
            return jsonify({
                "status": "error",
                "message": "O hash excede o limite de 80 bytes para o OP_RETURN!"
            }), 400

        # Cria uma nova carteira aleatória
        wallet_name = create_random_wallet()
        rpc = get_rpc_connection(wallet_name)

        # Gera um novo endereço para a carteira
        address = rpc.getnewaddress()

        # Retorna o endereço para pagamento
        return jsonify({
            "status": "pending_payment",
            "message": "Endereço gerado com sucesso. Envie o pagamento para registrar o hash.",
            "wallet_name": wallet_name,
            "address": address
        })

    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500

@app.route('/api/transaction/opreturn/confirm', methods=['POST'])
def confirm_opreturn_transaction():
    """
    Confirma o pagamento e registra o hash no OP_RETURN.
    """
    try:
        wallet_name = request.json.get('wallet_name')
        data = request.json.get('data')

        if not wallet_name or not data:
            return jsonify({
                "status": "error",
                "message": "Os campos 'wallet_name' e 'data' são obrigatórios."
            }), 400

        rpc = get_rpc_connection(wallet_name)

        # Verifica se há saldo suficiente na carteira
        balance = get_wallet_balance(wallet_name)
        if balance <= 0:
            return jsonify({
                "status": "error",
                "message": "Nenhum pagamento detectado na carteira."
            }), 400

        # Obtém UTXOs disponíveis
        utxos = rpc.listunspent(1)
        utxos = [utxo for utxo in utxos if utxo['spendable']]

        if not utxos:
            return jsonify({
                "status": "error",
                "message": "Sem fundos disponíveis para criar a transação."
            }), 400

        # Seleciona o primeiro UTXO disponível
        utxo = utxos[0]
        txid = utxo['txid']
        vout = utxo['vout']
        amount = utxo['amount']

        # Calcula a mudança (subtraindo a taxa de transação mínima)
        change_address = rpc.getrawchangeaddress()
        fee = Decimal('0.0001')
        change_amount = Decimal(amount) - fee

        if change_amount <= 0:
            return jsonify({"status": "error", "message": "Fundos insuficientes para cobrir a taxa de transação!"}), 400

        # Cria a transação com OP_RETURN
        outputs = [
            {"txid": txid, "vout": vout},
        ]
        destinations = {
            "data": data,
            change_address: float(change_amount)
        }

        # Cria, assina e envia a transação
        raw_tx = rpc.createrawtransaction(outputs, destinations)
        signed_tx = rpc.signrawtransactionwithwallet(raw_tx)
        sent_txid = rpc.sendrawtransaction(signed_tx['hex'])

        return jsonify({
            "status": "success",
            "message": "Hash registrado com sucesso no OP_RETURN!",
            "txid": sent_txid
        })

    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500
    

@app.route('/api/transaction/send', methods=['POST'])
def send_transaction():
    """
    Envia uma transação da carteira da plataforma para o endereço fornecido.
    """
    try:
        print("📌 Iniciando envio de transação pela API...")

        # Obtém os dados da requisição
        data = request.get_json()
        address = data.get("address")
        amount = data.get("amount")

        print(f"📌 Dados recebidos: endereço={address}, valor={amount}")

        # Valida os parâmetros
        if not address:
            return jsonify({"status": "error", "message": "O endereço é obrigatório."}), 400
        if not amount or not isinstance(amount, (int, float)):
            return jsonify({"status": "error", "message": "O valor deve ser numérico e maior que zero."}), 400

        # Define a carteira usada para a transação
        wallet_name = "platform_wallet"

        # Certifique-se de que a carteira está carregada
        rpc_admin = get_rpc_connection()
        wallets = rpc_admin.listwallets()
        if wallet_name not in wallets:
            print(f"⚠️ A carteira {wallet_name} não está carregada. Tentando carregar...")
            rpc_admin.loadwallet(wallet_name)

        # Conecta ao RPC com a carteira correta
        rpc = get_rpc_connection(wallet_name)
        print(f"📌 Conexão RPC estabelecida com a carteira {wallet_name}.")

        # Verifica saldo antes de enviar
        balance = rpc.getbalance()
        print(f"📌 Saldo disponível na carteira {wallet_name}: {balance} BTC.")

        if balance < amount:
            return jsonify({
                "status": "error",
                "message": f"Saldo insuficiente. Saldo disponível: {balance} BTC."
            }), 400

        # Garante que a taxa está definida corretamente
        rpc.settxfee(0.0001)
        print(f"📌 Taxa de transação definida como 0.0001 BTC.")

        # Envia a transação
        print(f"📌 Enviando {amount} BTC para {address}...")
        txid = rpc.sendtoaddress(address, float(amount))
        print(f"✅ Transação enviada com sucesso! TXID: {txid}")

        return jsonify({
            "status": "success",
            "message": "Transação enviada com sucesso!",
            "txid": txid
        })

    except JSONRPCException as e:
        print(f"⚠️ Erro RPC: {e}")
        return jsonify({"status": "error", "message": f"RPC error: {str(e)}"}), 400
    except Exception as e:
        print(f"⚠️ Erro inesperado: {e}")
        return jsonify({"status": "error", "message": f"Erro inesperado: {str(e)}"}), 500
    
    
@app.route('/api/transaction/<string:txid>', methods=['GET'])
def get_transaction_by_hash(txid):
    try:
        rpc = get_rpc_connection()
        transaction = rpc.getrawtransaction(txid, True)
        return jsonify({"status": "success", "message": "Transaction retrieved successfully!", "transaction": transaction})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    
@app.route('/api/transaction/count', methods=['GET'])
def get_transaction_count():
    try:
        rpc = get_rpc_connection()
        block_count = rpc.getblockcount()

        total_tx_count = 0
        for i in range(block_count + 1):
            block_hash = rpc.getblockhash(i)
            block = rpc.getblock(block_hash)
            total_tx_count += len(block.get('tx', []))

        return jsonify({"status": "success", "message": "Transaction count retrieved successfully!", "transaction_count": total_tx_count})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400

@app.route('/api/transactions/list', methods=['GET'])
def list_transactions():
    try:
        wallet_name = request.args.get('wallet_name', '')
        count = int(request.args.get('count', 10))
        skip = int(request.args.get('skip', 0))

        rpc = get_rpc_connection()
        
        if wallet_name:
            loaded_wallets = rpc.listwallets()
            if wallet_name not in loaded_wallets:
                rpc.loadwallet(wallet_name)
     
        transactions = rpc.listtransactions("*", count, skip)
        return jsonify({"status": "success", "message": "Transactions retrieved successfully!", "transactions": transactions})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Unexpected error: {str(e)}'}), 500
    
@app.route('/api/wallet/count', methods=['GET'])
def get_wallet_count():
    try:
        rpc = get_rpc_connection()
        wallets = rpc.listwallets()
        wallet_count = len(wallets)
        return jsonify({"status": "success", "message": "Wallet count retrieved successfully!", "wallet_count": wallet_count, "wallets": wallets})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400

# Adicione uma função de validação específica para sua criptomoeda
def is_valid_address(address):
    # Implemente a validação conforme as regras da sua blockchain
    # Exemplo básico: verificar comprimento e caracteres válidos
    return len(address) >= 25  # Ajuste conforme necessário

def get_wallet_balance_name(wallet_name):
    """Obtém o saldo da carteira."""
    rpc = get_rpc_connection(wallet_name)
    return rpc.getbalance()

@app.route('/api/wallet/balance/name/<string:wallet_name>')
def get_wallet_balance_name(wallet_name):
    
    if wallet_name:
        
        try:            
            balance = get_wallet_balance_name(wallet_name)      
            return jsonify({
                "status": "success",
                "message": "Wallet balance retrieved successfully!",
                "wallet_name": wallet_name,
                "balance": balance
            })
        except JSONRPCException as e:
            return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500
    
@app.route('/api/wallet/balance/all')
def get_wallet_balance_load():
    
    try:
        rpc = get_rpc_connection()
        
        # Obtém o saldo total da carteira carregada
        balance = rpc.getbalance()
        
        # Opcional: obter informações adicionais
        unconfirmed = rpc.getunconfirmedbalance()  # Se suportado
        # transactions = rpc.listtransactions("*", 10)  # Últimas 10 transações
        
        return jsonify({
            "status": "success",
            "message": "Current wallet balance retrieved successfully!",
            "balance": balance,
            "unconfirmed": unconfirmed,
            # "recent_transactions": transactions
        })
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Unexpected error: {str(e)}'}), 500  

@app.route('/api/wallet/balance/address/<string:address>')
def get_wallet_balance_by_address(address):
    
    try:
        
        if address:
            rpc = get_rpc_connection()
            balance = rpc.getreceivedbyaddress(address)
            return jsonify({
                "status": "success",
                "message": "Saldo recuperado com sucesso!",
                "address": address,
                "balance": balance
            })

        return jsonify({
            "status": "error",
            "message": "É necessário fornecer 'wallet_name' ou 'address'."
        }), 400
        
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500      
        

@app.route('/api/wallet/balance', defaults={'identifier': None}, methods=['GET'])
@app.route('/api/wallet/balance/<string:identifier>', methods=['GET'])
def get_wallet_balance(identifier):
    """
    Obtém o saldo de uma carteira específica pelo nome ou endereço.
    """
    try:
        # Verifica se o identificador foi passado como parâmetro na URL ou query string
        wallet_name = identifier or request.args.get('wallet_name')
        address = request.args.get('address')

        if wallet_name:
            rpc = get_rpc_connection(wallet_name)
            balance = rpc.getbalance()
            return jsonify({
                "status": "success",
                "message": "Saldo recuperado com sucesso!",
                "wallet_name": wallet_name,
                "balance": balance
            })

        if address:
            rpc = get_rpc_connection()
            balance = rpc.getreceivedbyaddress(address)
            return jsonify({
                "status": "success",
                "message": "Saldo recuperado com sucesso!",
                "address": address,
                "balance": balance
            })

        return jsonify({
            "status": "error",
            "message": "É necessário fornecer 'wallet_name' ou 'address'."
        }), 400

    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500
            
    
@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    try:
        wallet_name = request.json.get('wallet_name')
        if not wallet_name:
            return jsonify({"status": "error", "message": "Wallet name is required!"}), 400

        rpc = get_rpc_connection()
        result = rpc.createwallet(wallet_name)
        return jsonify({"status": "success", "message": "Wallet created successfully!", "result": result})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400

@app.route('/api/wallet/details/<string:wallet_name>', methods=['GET'])
def get_wallet_details(wallet_name):
    try:
        rpc = get_rpc_connection()
        loaded_wallets = rpc.listwallets()
        if wallet_name not in loaded_wallets:
            rpc.loadwallet(wallet_name)
        details = rpc.getwalletinfo()
        return jsonify({"status": "success", "message": "Wallet details retrieved successfully!", "details": details})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400


def get_new_address(wallet_name="platform_wallet"):
    """Solicita um novo endereço ao Bitcoin Core dentro do contexto de uma carteira."""
    try:
        rpc = get_rpc_connection(wallet_name)  # Certifica-se de que a conexão usa a carteira correta
        address = rpc.getnewaddress()
        print(f"Endereço gerado pelo nó (regtest): {address}")
        return address
    except JSONRPCException as e:
        print(f"Erro ao obter endereço do nó: {e}")
        raise


def initialize_wallet():
    """Inicializa a carteira padrão e gera blocos iniciais se necessário."""
    print("Verificando ou criando uma nova carteira...")
    
    print(f"Conectando a rede {NETWORK}...")
    ensure_wallet_exists("platform_wallet")

    print("Carregando carteira padrão para obter um endereço...")
    address = get_new_address("platform_wallet")  # Agora chamamos explicitamente a carteira correta   

    if get_rpc_connection("platform_wallet").getblockchaininfo()["chain"] == "regtest":
        print("Rede regtest detectada. Gerando blocos para ativação...")
        block_hashes = get_rpc_connection("platform_wallet").generatetoaddress(101, address)
        print(f"Blocos gerados: {len(block_hashes)}")
        print(f"Primeiro bloco: {block_hashes[0]}")

    return {'address': address}


def generate_blocks(wallet, num_blocks=101):
    """Gera blocos para a rede regtest."""
    address = wallet['address']
    try:
        block_hashes = rpc.generatetoaddress(num_blocks, address)
        print(f"Blocos gerados: {len(block_hashes)}")
        print(f"Primeiro bloco: {block_hashes[0]}")
    except Exception as e:
        print(f"Erro ao gerar blocos: {e}")

# RPC remote commands terminal
@app.route('/api/rpc-command', methods=['POST'])
def execute_rpc_command():
    try:
        command = request.json.get('command')
        args = request.json.get('args', [])

        if not command:
            return jsonify({"status": "error", "message": 'Empty command is not allowed!'}), 400

        rpc = get_rpc_connection()

        method = getattr(rpc, command, None)
        if not method:
            return jsonify({"status": "error", "message": f'Command "{command}" not recognized by Bitcoin Core!'}), 400

        typed_args = []
        for arg in args:
            try:
                if isinstance(arg, str) and arg.isdigit():
                    typed_args.append(int(arg))
                else:
                    typed_args.append(arg)
            except ValueError:
                typed_args.append(arg)

        result = method(*typed_args)
        return jsonify({"status": "success", "message": "Command executed successfully!", "result": result})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Unexpected error: {str(e)}'}), 500


if __name__ == '__main__':
    print("Inicializando o sistema...")
    wallet = initialize_wallet()
    
    print("Incializando banco de dados...")
    init_db()
            
    print("Sistema inicializado com sucesso!")
    app.run(debug=True, host='0.0.0.0', port=5000)




