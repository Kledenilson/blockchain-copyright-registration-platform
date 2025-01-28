from flask import Flask, request, jsonify
from flask_cors import CORS
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bitcoin.rpc import RawProxy
import os
from decimal import Decimal

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações de rede e RPC
RPC_USER = os.getenv('RPC_USER', 'myuser')
RPC_PASSWORD = os.getenv('RPC_PASSWORD', 'mypassword')
RPC_HOST = os.getenv('RPC_HOST', 'bitcoin-core')
RPC_PORT = int(os.getenv('RPC_PORT', 18443))

# Inicialização do cliente RPC
def get_rpc_connection():
    url = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
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

@app.route('/api/transaction/opreturn', methods=['POST'])
def create_opreturn_transaction():
    """
    Cria uma transação com OP_RETURN com base no conteúdo do arquivo enviado.
    """
    try:
        file = request.files.get('file')
        wallet_name = request.form.get('wallet_name', 'default_wallet')

        if not file or not allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": "Arquivo inválido! Permitidos: txt, pdf, doc, docx, jpg, jpeg, png, gif, mp3, wav, aac, ogg."
            }), 400

        data = file.read().hex()  # Converte o conteúdo do arquivo para hexadecimal

        # Validar tamanho do OP_RETURN (máximo de 80 bytes)
        if len(data) > 160:  # Cada byte é representado por 2 caracteres hexadecimais
            return jsonify({
                "status": "error",
                "message": "Os dados do OP_RETURN excedem o limite de 80 bytes!"
            }), 400

        rpc = get_rpc_connection()

        # Garante que a carteira está carregada
        if wallet_name not in rpc.listwallets():
            rpc.loadwallet(wallet_name)

        # Obter UTXOs disponíveis
        utxos = rpc.listunspent(1)  # Confirmação mínima de 1 bloco
        if not utxos:
            return jsonify({"status": "error", "message": "Sem fundos disponíveis na carteira!"}), 400

        # Selecionar o primeiro UTXO disponível
        utxo = utxos[0]
        txid = utxo['txid']
        vout = utxo['vout']
        amount = utxo['amount']

        # Calcular mudança (subtraindo taxa de transação mínima)
        change_address = rpc.getrawchangeaddress()
        fee = Decimal('0.0001')  # Taxa mínima para regtest
        change_amount = Decimal(amount) - fee

        if change_amount <= 0:
            return jsonify({"status": "error", "message": "Fundos insuficientes para cobrir a taxa de transação!"}), 400

        print(f"Endereço de mudança: {change_address}")
        print(f"OP_RETURN data: {data}")

        # Criar transação com OP_RETURN
        outputs = [
            {"txid": txid, "vout": vout},
        ]
        destinations = {
            "data": data,  # OP_RETURN
            change_address: float(change_amount)  # Mudança
        }

        # Criar, assinar e enviar a transação
        raw_tx = rpc.createrawtransaction(outputs, destinations)
        signed_tx = rpc.signrawtransactionwithwallet(raw_tx)
        sent_txid = rpc.sendrawtransaction(signed_tx['hex'])

        return jsonify({
            "status": "success",
            "message": "Transação criada e enviada com sucesso!",
            "txid": sent_txid
        })
    except JSONRPCException as e:
        return jsonify({"status": "error", "message": f'Erro RPC: {str(e)}'}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f'Erro inesperado: {str(e)}'}), 500


@app.route('/api/transaction/opreturn/<string:txid>', methods=['GET'])
def get_opreturn_transaction(txid):
    """
    Consulta os dados do OP_RETURN de uma transação.
    """
    try:
        rpc = get_rpc_connection()
        raw_tx = rpc.getrawtransaction(txid, True)
        vouts = raw_tx.get('vout', [])
        op_return_data = None

        # Buscar saída OP_RETURN
        for vout in vouts:
            script_pubkey = vout.get('scriptPubKey', {})
            if script_pubkey.get('asm', '').startswith('OP_RETURN'):
                op_return_data = script_pubkey.get('hex', None)
                break

        if not op_return_data:
            return jsonify({"status": "error", "message": "Nenhuma saída OP_RETURN encontrada na transação."}), 404

        return jsonify({
            "status": "success",
            "message": "Dados OP_RETURN recuperados com sucesso!",
            "op_return_data": op_return_data
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


@app.route('/api/wallet/balance/', defaults={'address': None})
@app.route('/api/wallet/balance/<string:address>')
def get_wallet_balance(address):
    
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


def ensure_wallet_exists(wallet_name="default_wallet"):
    """Garante que uma carteira exista no nó bitcoin-core."""
    try:
        wallets = rpc.listwallets()
        if wallet_name not in wallets:
            print(f"Criando carteira '{wallet_name}'...")
            rpc.createwallet(wallet_name, False)
        else:
            print(f"A carteira '{wallet_name}' já existe.")
    except Exception as e:
        print(f"Erro ao verificar ou criar carteira: {e}")
        raise

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

    # Manter o servidor ativo
    # while True:
    #     try:
    #         time.sleep(10)
    #     except KeyboardInterrupt:
    #         print("Servidor encerrado.")
    #         break

    app.run(debug=True, host='0.0.0.0', port=5000)

# if __name__ == '__main__':
#     print("Inicializando o sistema...")
#     wallet = initialize_wallet()

#     if rpc.getblockchaininfo()["chain"] == "regtest":
#         print("Rede regtest detectada. Gerando blocos para ativação...")
#         generate_blocks(wallet)

#     print("Sistema inicializado com sucesso!")


