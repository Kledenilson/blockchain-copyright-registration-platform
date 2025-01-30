import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import io from "socket.io-client";

// Inicializa o WebSocket
const socket = io("http://localhost:5000");

export default function History() {
  const [transaction, setTransaction] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const router = useRouter();
  const { address } = router.query; // Obtém o endereço da query string

  // Busca as transações da API
  const fetchTransactions = async () => {
    if (!address) return; // Aguarda o endereço estar disponível
    try {
      const response = await axios.get(
        `http://localhost:5000/api/transactions/${address}`
      );
      console.log(response);
      setTransaction(response.data);
      setTransactions(response.data.transactions);
    } catch (error) {
      console.error("Error fetching transactions:", error);
    }
  };

  // Atualiza as transações em tempo real via WebSocket
  useEffect(() => {
    fetchTransactions();

    socket.on("payment_confirmed", (data) => {
      console.log("New transaction confirmed:", data);
      // Adiciona ou atualiza a transação na lista existente
      setTransactions((prev) => {
        const existingTx = prev.find((tx) => tx.txid === data.txid);
        if (existingTx) {
          return prev.map((tx) =>
            tx.txid === data.txid ? { ...tx, ...data } : tx
          );
        } else {
          return [...prev, data];
        }
      });
    });

    return () => {
      socket.off("payment_confirmed");
    };
  }, [address]);

  // Busca detalhes de uma transação específica
  const fetchTransactionDetails = async (txids) => {
    try {
      const response = await axios.get(
        `http://localhost:5000/api/transaction/${txids}`
      );
      setSelectedTransaction(response.data.transaction);
    } catch (error) {
      console.error("Error fetching transaction details:", error);
    }
  };

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4 text-primary">Transaction Details</h1>
      <div className="card shadow p-4">
        <h3 className="card-title">Transactions for Address: {address}</h3>
        <div className="card-body">
          {transactions.length === 0 ? (
            <p className="text-center text-muted">No transactions found for this address.</p>
          ) : (
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>TXID</th>
                  <th>Amount</th>
                  <th>Status</th>                 
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.txids}>
                    <td>
                      <button
                        className="btn btn-link p-0"
                        onClick={() => fetchTransactionDetails(tx.txids)}
                      >
                        {tx.txids}
                      </button>
                    </td>
                    <td>{tx.amount} BTC</td>
                    <td>
                      <span
                        className={`badge ${
                          transaction.status === "confirmed"
                            ? "bg-success"
                            : "bg-warning text-dark"
                        }`}
                      >
                        {transaction.status}
                      </span>
                    </td>                    
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detalhes da transação selecionada */}
      {selectedTransaction && (
        <div className="card shadow p-4 mt-4">
          <h3 className="card-title">Transaction Details</h3>
          <div className="card-body">
            <p><strong>TXID:</strong> {selectedTransaction.txid}</p>
            <p><strong>Received By:</strong> {selectedTransaction.address}</p>
            <p><strong>Amount:</strong> {selectedTransaction.amount} BTC</p>
            <p><strong>Status:</strong> 
              <span className={`badge ${selectedTransaction.status === "confirmed" ? "bg-success" : "bg-warning text-dark"}`}>
                {selectedTransaction.status}
              </span>
            </p>
            <p><strong>Date:</strong> {selectedTransaction.time
              ? new Date(selectedTransaction.time * 1000).toLocaleString("pt-BR", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "No Date Available"}</p>
          </div>
        </div>
      )}
    </div>
  );
}
