import { useEffect, useState } from "react";
import axios from "axios";
import io from "socket.io-client";

const socket = io("http://localhost:5000");

export default function History() {
  const [transactions, setTransactions] = useState([]);

  const fetchTransactions = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/transactions");
      setTransactions(response.data.transactions);
    } catch (error) {
      console.error("Erro ao buscar transações:", error);
    }
  };

  useEffect(() => {
    fetchTransactions();
    
    socket.on("payment_confirmed", (data) => {
      console.log("Nova transação confirmada:", data);
      fetchTransactions();
    });

    return () => {
      socket.off("payment_confirmed");
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-5">
      <h1 className="text-2xl font-bold mb-5">Histórico de Transações</h1>
      <div className="bg-white shadow-lg rounded p-6 w-full max-w-3xl">
        {transactions.length === 0 ? (
          <p className="text-center text-gray-600">Nenhuma transação encontrada.</p>
        ) : (
          <ul>
            {transactions.map((tx) => (
              <li key={tx.txid} className="p-4 border-b last:border-none">
                <p><b>TXID:</b> {tx.txid}</p>
                <p><b>Status:</b> {tx.status}</p>
                <p><b>Data:</b> {new Date(tx.timestamp).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
