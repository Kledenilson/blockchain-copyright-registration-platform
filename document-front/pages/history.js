import { useEffect, useState } from "react";
import axios from "axios";
import io from "socket.io-client";

const socket = io("http://localhost:5000");

export default function History() {
  const [transactions, setTransactions] = useState([]);

  // Função para buscar transações da API
  const fetchTransactions = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/transactions/list");      
      setTransactions(response.data.transactions);
    } catch (error) {
      console.error("Error fetching transactions:", error);
    }
  };

  // Atualiza transações em tempo real via WebSocket
  useEffect(() => {
    fetchTransactions();

    socket.on("payment_confirmed", (data) => {
      console.log("New transaction confirmed:", data);
      fetchTransactions(); // Atualiza a lista em tempo real
    });

    return () => {
      socket.off("payment_confirmed");
    };
  }, []);

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4 text-primary">Transaction History</h1>
      <div className="card shadow p-4">
        <h3 className="card-title">Recent Transactions</h3>
        <div className="card-body">
          {transactions.length === 0 ? (
            <p className="text-center text-muted">No transactions found.</p>
          ) : (
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>TXID</th>
                  <th>Address</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.txid}>
                    <td>{tx.txid}</td>
                    <td>{tx.address}</td>
                    <td>
                      <span
                        className={`badge ${
                          transactions.status === "confirmed"
                            ? "bg-success"
                            : "bg-warning text-dark"
                        }`}
                      >
                        {transactions.status}
                      </span>
                    </td>
                    <td>{new Date(tx.time).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
