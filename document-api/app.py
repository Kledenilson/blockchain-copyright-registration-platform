from flask import Flask, request, jsonify
from flask_cors import CORS
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bitcoin.rpc import RawProxy
import os
import time, random
from decimal import Decimal

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações de rede e RPC
RPC_USER = os.getenv('RPC_USER', 'myuser')
RPC_PASSWORD = os.getenv('RPC_PASSWORD', 'mypassword')
RPC_HOST = os.getenv('RPC_HOST', 'bitcoin-core')
RPC_PORT = int(os.getenv('RPC_PORT', 18443))

# Inicialização do cliente RPC
def get_rpc_connection(wallet_name=None):
    url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
    if wallet_name:
        url += f"/wallet/{wallet_name}"
    return AuthServiceProxy(url)

rpc = get_rpc_connection();

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
def ensure_wallet_exists(wallet_name="default_wallet"):
    """
    Garante que uma carteira exista no nó Bitcoin Core.
    """
    try:
        rpc = get_rpc_connection()
        wallets = rpc.listwallets()
        if wallet_name not in wallets:
            rpc.createwallet(wallet_name)
            time.sleep(0.5)  # Aguarda para evitar problemas de bloqueio
        else:
            print(f"A carteira '{wallet_name}' já existe.")
    except Exception as e:
        print(f"Erro ao verificar ou criar carteira: {e}")
        raise

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
    try:
        address = request.json.get('address')
        amount = request.json.get('amount')

        if not address or not amount:
            return jsonify({"status": "error", "message": '"address" and "amount" parameters are required!'}), 400

        rpc = get_rpc_connection()
        txid = rpc.sendtoaddress(address, amount)
        return jsonify({"status": "success", "message": "Transaction sent successfully!", "txid": txid})
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
    
    
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

@app.route('/api/wallet/balance/', defaults={'address': None, 'walle_name': None})
@app.route('/api/wallet/balance/<string:wallet_name>')
@app.route('/api/wallet/balance/<string:address>')
def get_wallet_balance(address, wallet_name=''):
    
    if address:
        
        try:
            rpc = get_rpc_connection()
            
            # Verifica se o endereço é válido (implemente sua lógica de validação)
            if not is_valid_address(address):  # Você precisa criar esta função
                return jsonify({"status": "error", "message": "Invalid wallet address"}), 400
                
            # Obtém o saldo usando o endereço (ajuste para o método correto da sua RPC)
            balance = rpc.getreceivedbyaddress(address)  # Método comum em muitas implementações RPC
            
            return jsonify({
                "status": "success",
                "message": "Wallet balance retrieved successfully!",
                "address": address,
                "balance": balance
            })
        except JSONRPCException as e:
            return jsonify({"status": "error", "message": f'RPC error: {str(e)}'}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f'Unexpected error: {str(e)}'}), 500
        
    elif wallet_name:   
        
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
        
    else:
        
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


def get_new_address():
    """Solicita um novo endereço ao bitcoin-core."""
    try:
        address = rpc.getnewaddress()
        print(f"Endereço gerado pelo nó (regtest): {address}")
        return address
    except Exception as e:
        print(f"Erro ao obter endereço do nó: {e}")
        raise

def initialize_wallet():
    """Inicializa a carteira, solicitando endereço ao nó."""
    print("Verificando ou criando uma nova carteira...")
    ensure_wallet_exists()
    address = get_new_address()
    print("Carteira configurada com sucesso.")
    return {
        'address': address
    }

def generate_blocks(wallet, num_blocks=101):
    """Gera blocos para a rede regtest."""
    address = wallet['address']
    try:
        block_hashes = rpc.generatetoaddress(num_blocks, address)
        print(f"Blocos gerados: {len(block_hashes)}")
        print(f"Primeiro bloco: {block_hashes[0]}")
    except Exception as e:
        print(f"Erro ao gerar blocos: {e}")

if __name__ == '__main__':
    print("Inicializando o sistema...")
    wallet = initialize_wallet()

    if rpc.getblockchaininfo()["chain"] == "regtest":
        print("Rede regtest detectada. Gerando blocos para ativação...")
        generate_blocks(wallet)

    print("Sistema inicializado com sucesso!")

if __name__ == '__main__':    
    app.run(debug=True, host='0.0.0.0', port=5000)




